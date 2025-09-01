from .extensions import db
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON
import secrets


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(64), default="user")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to refresh tokens
    refresh_tokens = db.relationship(
        "RefreshToken", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    client_info = db.Column(db.String(512), nullable=True)  # Store user-agent, IP, etc.

    @staticmethod
    def generate_token():
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(64)

    @property
    def is_expired(self):
        """Check if token is expired"""
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    @property
    def is_revoked(self):
        """Check if token is revoked"""
        return self.revoked_at is not None

    @property
    def is_valid(self):
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired and not self.is_revoked

    def revoke(self):
        """Revoke the token"""
        self.revoked_at = datetime.now(timezone.utc)


class Market(db.Model):
    __tablename__ = "markets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    county = db.Column(db.String(128))
    # optional precomputed friction/distance map stored as JSON: { "Nairobi": 100, ... }
    friction_map = db.Column(JSON, nullable=True)


class MarketPrice(db.Model):
    __tablename__ = "market_prices"
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey("markets.id"), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    price_kg = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class WeatherData(db.Model):
    __tablename__ = "weather_data"
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey("markets.id"))
    timestamp = db.Column(db.DateTime)
    rain_mm = db.Column(db.Float)
    weather_code = db.Column(db.String(32))
    weather_index = db.Column(db.Float)  # normalized index used by estimator
    raw = db.Column(JSON, nullable=True)


class ModelState(db.Model):
    __tablename__ = "model_state"
    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(JSON)
