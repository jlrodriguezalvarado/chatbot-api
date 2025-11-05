import os
import json
import click
from flask.cli import with_appcontext
from app.aplication import db
from app.aplication.models.apikey import ApiKey
from app.aplication.models.post import Post
from flask import current_app
from sqlalchemy import create_engine
import secrets
import requests


from app.aplication.vector_store import build_vector_store_from_posts


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

@click.command(name='populate_wordpress')
@with_appcontext
def populate_wordpress():
    """Populate WordPress with wine reviews from wines.json."""
    # Get the path to the wines.json file (relative to commands.py location)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    wines_file = os.path.join(current_dir, 'mockupdata', 'wines.json')
    
    # Read the wines.json file
    try:
        with open(wines_file, 'r', encoding='utf-8') as f:
            wines = json.load(f)
    except FileNotFoundError:
        click.echo(f'Error: File not found at {wines_file}')
        return
    except json.JSONDecodeError as e:
        click.echo(f'Error: Invalid JSON in wines.json: {e}')
        return
    
    # The WordPress REST API endpoint is running on the `chatbot_api_wordpress` service
    # When running inside the Docker network, services can communicate with each other
    # using their service names.
    wp_user = os.environ.get('WP_USER')
    wp_password = os.environ.get('WP_PASSWORD')
    
    successful = 0
    failed = 0

    # Send each wine review to WordPress
    for wine in wines:
        post = {
            'title': wine.get('title', ''),
            'content': wine.get('content', ''),
            'status': wine.get('status', 'publish')
        }
        
        response = requests.post('http://chatbot_api_wordpress/wp-json/wp/v2/posts', json=post, auth=(wp_user, wp_password))
        if response.status_code == 201:
            click.echo(f'Post "{post["title"]}" created successfully.')
            successful += 1
        else:
            click.echo(f'Failed to create post "{post["title"]}". Status code: {response.status_code}')
            failed += 1
            break
    
    click.echo(f'\nSummary: {successful} posts created successfully, {failed} failed.')

@click.command(name='import_wordpress_posts')
@with_appcontext
def import_wordpress_posts():
    """Import posts from WordPress."""
    response = requests.get('http://chatbot_api_wordpress/wp-json/wp/v2/posts?per_page=100')
    if response.status_code == 200:
        posts = response.json()
        for post_data in posts:
            title = post_data['title']['rendered']
            content = post_data['content']['rendered']

            # Check if the post already exists
            if not Post.query.filter_by(title=title).first():
                post = Post(title=title, content=content)
                db.session.add(post)
        db.session.commit()
        click.echo(f'{len(posts)} posts imported successfully.')
    else:
        click.echo(f'Failed to import posts. Status code: {response.status_code}')

@click.command(name='import_wines_from_json')
@with_appcontext
def import_wines_from_json():
    """Import wine reviews from wines.json into PostgreSQL database."""
    # Get the path to the wines.json file (relative to commands.py location)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    wines_file = os.path.join(current_dir, 'mockupdata', 'wines.json')
    
    # Read the wines.json file
    try:
        with open(wines_file, 'r', encoding='utf-8') as f:
            wines = json.load(f)
    except FileNotFoundError:
        click.echo(f'Error: File not found at {wines_file}')
        return
    except json.JSONDecodeError as e:
        click.echo(f'Error: Invalid JSON in wines.json: {e}')
        return
    
    created = 0
    skipped = 0
    
    # Import each wine review into the database
    for wine in wines:
        title = wine.get('title', '').strip()
        content = wine.get('content', '').strip()
        
        # Skip if title or content is empty
        if not title or not content:
            click.echo(f'Skipping wine with empty title or content: {title}')
            skipped += 1
            continue
        
        # Check if the post already exists
        if Post.query.filter_by(title=title).first():
            click.echo(f'Post "{title}" already exists, skipping.')
            skipped += 1
            continue
        
        # Create new post (ignoring the 'status' field)
        post = Post(title=title, content=content)
        db.session.add(post)
        created += 1
        click.echo(f'Added post "{title}" to database.')
    
    # Commit all changes
    try:
        db.session.commit()
        click.echo(f'\nSummary: {created} posts created successfully, {skipped} skipped.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error committing to database: {e}')


@click.command(name='build_vs')
@with_appcontext
@click.option('--table', default='post', help='Nombre de la tabla (post/posts).')
@click.option('--limit', default=None, type=int, help='Limitar cantidad (pruebas).')
def build_vs(table, limit):
    """
    Crea/actualiza el Vector Store desde PostgreSQL con los posts (title, content).
    Guarda el ID en instance/vector_store_id.
    """
    db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        raise click.UsageError("SQLALCHEMY_DATABASE_URI no configurada")

    engine = create_engine(db_url)
    vs_id = build_vector_store_from_posts(engine, table=table, limit=limit)
    click.echo(f"VECTOR_STORE_ID: {vs_id} (guardado en {current_app.config['VECTOR_STORE_ID_FILE']})")