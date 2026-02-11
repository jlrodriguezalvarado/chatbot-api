from app.aplication import create_app, db
from app.aplication.models.apikey import ApiKey
from app.aplication.models.post import Post
from app.aplication.models.vector_store_record import VectorStoreRecord
from app.aplication.commands import create_apikey, list_apikeys, populate_wordpress, import_wordpress_posts, build_vs, delete_vs, generate_secret_key
from flask_cors import CORS
import os

app = create_app()

# --- CORS ---
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080"
)
origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]

CORS(
    app,
    resources={
        r"/chat/*": {"origins": origins}   # ajusta el prefijo si tus endpoints cambian
    },
    supports_credentials=False,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)


app.cli.add_command(create_apikey)
app.cli.add_command(list_apikeys)
app.cli.add_command(generate_secret_key)
app.cli.add_command(populate_wordpress)
app.cli.add_command(import_wordpress_posts)
app.cli.add_command(build_vs)
app.cli.add_command(delete_vs)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'ApiKey': ApiKey, 'Post': Post, 'VectorStoreRecord': VectorStoreRecord}

if __name__ == '__main__':
    # Set the FLASK_APP environment variable if it's not already set
    os.environ.setdefault('FLASK_APP', 'run.py')

    # Create the default admin user if it doesn't exist
    with app.app_context():
        if not ApiKey.query.filter_by(name='admin').first():
            from app.aplication.commands import create_apikey
            import click
            from flask.cli import with_appcontext

            @click.command(name='create_admin')
            @with_appcontext
            def create_admin():
                """Create the default admin user."""
                key = 'admin-secret-key'
                api_key = ApiKey(name='admin', key=key)
                db.session.add(api_key)
                db.session.commit()
                click.echo(f'Admin API key: {key}')

            app.cli.add_command(create_admin)
            import subprocess
            subprocess.run(['flask', 'create_admin'])

    app.run(host='0.0.0.0')
