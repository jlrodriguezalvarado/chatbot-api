import os

class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     'postgresql://user:password@db:5432/appdb'
    # SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@db:5432/appdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenAI / Vector Store
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    VECTOR_STORE_NAME = os.environ.get('VECTOR_STORE_NAME', 'licores-site')
    # En docker-compose montas ./instance -> /app/instance
    VECTOR_STORE_ID_FILE = os.environ.get('VECTOR_STORE_ID_FILE', '/app/instance/vector_store_id')
