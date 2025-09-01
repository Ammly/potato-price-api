from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from flask import current_app

db = SQLAlchemy()
migrate = Migrate()

# Initialize limiter without storage initially - will be configured in app factory
limiter = Limiter(key_func=get_remote_address)

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        url = current_app.config.get("REDIS_URL")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client
