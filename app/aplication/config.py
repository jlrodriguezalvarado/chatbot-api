import os

class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     'postgresql://user:password@db:5432/appdb'
    # SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@db:5432/appdb'
    # MySQL database URI
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'.format(
            user=os.environ.get('MYSQL_USER', 'wordpress'),
            password=os.environ.get('MYSQL_PASSWORD', 'password'),
            host=os.environ.get('MYSQL_HOST', 'chatbot_api_wordpress_db'),
            port=os.environ.get('MYSQL_PORT', '3306'),
            database=os.environ.get('MYSQL_DATABASE', 'wordpress')
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenAI / Vector Store
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    VECTOR_STORE_NAME = os.environ.get('VECTOR_STORE_NAME', 'licores-site')
    # En docker-compose montas ./instance -> /app/instance
    VECTOR_STORE_ID_FILE = os.environ.get('VECTOR_STORE_ID_FILE', '/app/instance/vector_store_id')

    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS',
        'http://localhost:8080,http://127.0.0.1:8080'
    )
