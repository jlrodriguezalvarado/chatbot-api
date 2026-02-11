from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.aplication.config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    # Importar modelos para que Flask-Migrate los detecte
    from app.aplication.models import apikey, post, vector_store_record  # noqa
    
    from app.aplication.routes import main
    app.register_blueprint(main)

    return app
