import os
import json
import click
from flask.cli import with_appcontext
from app.aplication import db
from app.aplication.models.apikey import ApiKey
from app.aplication.models.post import Post
from app.aplication.models.vector_store_record import VectorStoreRecord
from flask import current_app
from sqlalchemy import create_engine
import secrets
import requests


from app.aplication.vector_store import build_vector_store_from_posts, delete_vector_store


@click.command(name='generate_secret_key')
def generate_secret_key():
    """Generate a secure random SECRET_KEY for Flask (Python). Use in .env as SECRET_KEY=..."""
    key = secrets.token_hex(32)
    click.echo(f"# Add to .env or config:\nSECRET_KEY={key}")


@click.command(name='create_apikey')
@with_appcontext
@click.argument('name')
def create_apikey(name):
    """Generate a new API key."""
    key = secrets.token_hex(32)
    api_key = ApiKey(name=name, key=key)
    db.session.add(api_key)
    db.session.commit()
    click.echo(f'API key for {name}: {key}')

@click.command(name='list_apikeys')
@with_appcontext
def list_apikeys():
    """List all API keys."""
    keys = ApiKey.query.all()
    for key in keys:
        click.echo(f'{key.name}: {key.key}')

def _get_wp_jwt_token():
    """
    Request JWT from WordPress jwt-auth/v1/token. Returns the token string or None on failure.
    Uses WP_USER and WP_PASSWORD for credentials.
    """
    base_url = os.environ.get('WP_BASE_URL', 'http://chatbot_api_wordpress')
    wp_user = os.environ.get('WP_USER')
    wp_password = os.environ.get('WP_PASSWORD')
    if not wp_user or not wp_password:
        return None
    url = f'{base_url.rstrip("/")}/wp-json/jwt-auth/v1/token'
    try:
        resp = requests.post(
            url,
            json={"username": wp_user, "password": wp_password},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("token") or (data.get("data") or {}).get("token")
    except requests.RequestException:
        return None


def _get_xtrawine_wines_path():
    """Path to xtrawine_wines.json: project root or current_app.instance_path parent."""
    root = os.environ.get('CHATBOT_API_ROOT')
    if root and os.path.isfile(os.path.join(root, 'xtrawine_wines.json')):
        return os.path.join(root, 'xtrawine_wines.json')
    # Fallback: parent of app directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for base in (current_dir, os.path.join(current_dir, '..', '..')):
        path = os.path.join(base, 'xtrawine_wines.json')
        if os.path.isfile(path):
            return os.path.abspath(path)
    return os.path.abspath(os.path.join(current_dir, '..', '..', 'xtrawine_wines.json'))


@click.command(name='populate_wordpress')
@with_appcontext
def populate_wordpress():
    """Load wines from xtrawine_wines.json into WordPress/WooCommerce via Vinum plugin API."""
    wines_file = _get_xtrawine_wines_path()
    try:
        with open(wines_file, 'r', encoding='utf-8') as f:
            wines = json.load(f)
    except FileNotFoundError:
        click.echo(f'Error: File not found at {wines_file}')
        return
    except json.JSONDecodeError as e:
        click.echo(f'Error: Invalid JSON in xtrawine_wines.json: {e}')
        return

    if not isinstance(wines, list):
        click.echo('Error: xtrawine_wines.json must be a JSON array of wine objects.')
        return

    wp_user = os.environ.get('WP_USER')
    wp_password = os.environ.get('WP_PASSWORD')
    if not wp_user or not wp_password:
        click.echo('Error: WP_USER and WP_PASSWORD must be set for REST API auth.')
        return

    token = _get_wp_jwt_token()
    if not token:
        click.echo('Error: Could not obtain JWT from WordPress (check WP_BASE_URL and jwt-auth/v1/token).')
        return

    base_url = os.environ.get('WP_BASE_URL', 'http://chatbot_api_wordpress')
    url = f'{base_url.rstrip("/")}/wp-json/vinum/v1/products'
    headers = {"Authorization": f"Bearer {token}"}
    successful = 0
    failed = 0

    for i, wine in enumerate(wines):
        if not isinstance(wine, dict) or not wine.get('product', {}).get('name'):
            click.echo(f'Skipping item {i + 1}: missing product.name')
            failed += 1
            continue
        name = wine['product']['name']
        try:
            response = requests.post(url, json=wine, headers=headers, timeout=60)
            if response.status_code in (200, 201):
                click.echo(f'Product "{name}" created successfully.')
                successful += 1
            else:
                click.echo(f'Failed "{name}". Status: {response.status_code} - {response.text[:200]}')
                failed += 1
        except requests.RequestException as e:
            click.echo(f'Failed "{name}": {e}')
            failed += 1

    click.echo(f'\nSummary: {successful} products created, {failed} failed.')

def sync_wordpress_posts():
    """Import/sync wine products from WordPress (Vinum plugin API) into the local post table.
    Performs upsert: creates new posts or updates existing ones (matched by wp_id or title).
    Returns tuple (total_created, total_updated). Raises on failure."""
    base_url = os.environ.get('WP_BASE_URL', 'http://chatbot_api_wordpress')
    url_base = f'{base_url.rstrip("/")}/wp-json/vinum/v1/products'
    token = _get_wp_jwt_token()
    if not token:
        raise RuntimeError("Could not obtain JWT from WordPress (check WP_BASE_URL and jwt-auth/v1/token).")
    headers = {"Authorization": f"Bearer {token}"}
    per_page = 100
    page = 1
    total_created = 0
    total_updated = 0

    while True:
        response = requests.get(
            url_base,
            params={'per_page': per_page, 'page': page},
            headers=headers,
            timeout=30
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch products from WordPress. Status: {response.status_code}")
        data = response.json()
        products = data.get('products') or []
        if not products:
            break
        for item in products:
            wp_id = item.get('id')
            title = (item.get('title') or '').strip()
            content = (item.get('content') or '').strip()
            product_url = (item.get('product_url') or '').strip() or None
            wine_data = item.get('wine_data')
            if not title:
                continue
            existing = Post.query.filter_by(wp_id=wp_id).first() if wp_id else None
            if not existing:
                existing = Post.query.filter_by(title=title).first()
            if existing:
                existing.title = title
                existing.content = content
                existing.product_url = product_url
                existing.wine_data = wine_data
                if wp_id is not None:
                    existing.wp_id = wp_id
                total_updated += 1
            else:
                post = Post(
                    title=title,
                    content=content,
                    wp_id=wp_id,
                    product_url=product_url,
                    wine_data=wine_data
                )
                db.session.add(post)
                total_created += 1
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise RuntimeError(f"Error committing: {e}") from e
        if len(products) < per_page:
            break
        page += 1

    return total_created, total_updated


@click.command(name='import_wordpress_posts')
@with_appcontext
def import_wordpress_posts():
    """Import wine products from WordPress (Vinum plugin API) into the local post table."""
    try:
        created, updated = sync_wordpress_posts()
        click.echo(f'Done. Created: {created}, Updated: {updated}.')
    except RuntimeError as e:
        click.echo(f'Error: {e}')

@click.command(name='build_vs')
@with_appcontext
@click.option('--table', default='post', help='Table name (id, title, content). Use "post" for wines imported from WP.')
@click.option('--limit', default=None, type=int, help='Limit number of rows (for testing).')
def build_vs(table, limit):
    """
    Build/update the Vector Store from the DB table (id, title, content).
    Use after import_wordpress_posts so the post table has wine content. Saves VS id to instance/vector_store_id.
    """
    db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        raise click.UsageError("SQLALCHEMY_DATABASE_URI is not configured")

    engine = create_engine(db_url)
    vs_id = build_vector_store_from_posts(engine, table=table, limit=limit)
    click.echo(f"VECTOR_STORE_ID: {vs_id} (guardado en {current_app.config['VECTOR_STORE_ID_FILE']})")


@click.command(name='delete_vs')
@with_appcontext
@click.argument('vector_store_id')
def delete_vs(vector_store_id):
    """
    Delete a Vector Store in OpenAI and its associated files.
    Also removes local files (vector_store_id and assistant_id) if they reference this VS.
    """
    try:
        delete_vector_store(vector_store_id)
        deleted = VectorStoreRecord.query.filter_by(vector_store_id=vector_store_id.strip()).delete()
        db.session.commit()
        if deleted:
            click.echo(f"Removed {deleted} record(s) from vector_store_record table.")
        click.echo("Done.")
    except ValueError as e:
        raise click.BadParameter(str(e))
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)