import click
from flask.cli import with_appcontext
from app.aplication import db
from app.aplication.models.apikey import ApiKey
from app.aplication.models.post import Post
import secrets
import requests
from faker import Faker

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
    """Populate WordPress with 100 wine reviews."""
    fake = Faker()
    for _ in range(100):
        title = f"Wine Review: {fake.word().capitalize()}"
        content = fake.paragraph(nb_sentences=10)
        post = {
            'title': title,
            'content': content,
            'status': 'publish'
        }
        # The WordPress REST API endpoint is assumed to be running on the `wordpress` service
        # at port 80. In a local setup, this would be accessible via `http://localhost:8080`.
        # When running inside the Docker network, services can communicate with each other
        # using their service names.
        response = requests.post('http://wordpress/wp-json/wp/v2/posts', json=post, auth=('admin', 'password'))
        if response.status_code == 201:
            click.echo(f'Post "{title}" created successfully.')
        else:
            click.echo(f'Failed to create post "{title}". Status code: {response.status_code}')

@click.command(name='import_wordpress_posts')
@with_appcontext
def import_wordpress_posts():
    """Import posts from WordPress."""
    response = requests.get('http://wordpress/wp-json/wp/v2/posts?per_page=100')
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
