"""
Flask-Migrate management script for database migrations
"""
import os
from flask.cli import FlaskGroup
from app.main import create_app
from app.extensions import db

app = create_app()
cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
