import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/potato_api"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-key")
    JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "900"))

    # Rate limiting - use Redis database 1 for rate limiting
    RATELIMIT_STORAGE_URL = os.getenv(
        "RATELIMIT_STORAGE_URL",
        os.getenv("REDIS_URL", "redis://localhost:6379/0").replace("/0", "/1"),
    )


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = "production"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Use Redis for rate limiting in tests to avoid warnings
    RATELIMIT_STORAGE_URL = "redis://redis:6379/1"
    # Disable rate limiting entirely in tests
    RATELIMIT_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
