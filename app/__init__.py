from flask import Flask
from config import Config

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app, engine_options={'pool_pre_ping': True, 'pool_recycle': 280})
migrate = Migrate(app, db)

app.app_context().push()

from app import routes, models