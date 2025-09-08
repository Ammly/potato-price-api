from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from flask import current_app
import os

db = SQLAlchemy()
migrate = Migrate()

# Initialize limiter with Redis storage URI from environment
def get_limiter_storage_uri():
    """Get the Redis storage URI for rate limiting"""
    storage_url = os.getenv("RATELIMIT_STORAGE_URL")
    if not storage_url:
        # Fallback to REDIS_URL with different database
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        storage_url = redis_url.replace("/0", "/1")
    return storage_url

# Initialize limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_limiter_storage_uri()
)

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        url = current_app.config.get("REDIS_URL")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client
