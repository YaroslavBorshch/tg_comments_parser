import os
from dotenv import load_dotenv
load_dotenv()

class Config(object):
    # Flask-configuration
    SECRET_KEY = os.environ.get('FLASK_KEY')

    # SQLAlchemy-configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('POSTGRES_DB_LINK')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
