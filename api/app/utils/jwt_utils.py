import os
import time
import jwt
from datetime import datetime, timezone, timedelta

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALG = "HS256"
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "900"))  # default 15m
REFRESH_TOKEN_EXP_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXP_DAYS", "30")
)  # default 30 days


def create_access_token(sub: str, extra_claims: dict | None = None):
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "iat": now,
        "exp": now + JWT_EXP_SECONDS,
        "iss": "potato-price-api",
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token


def create_refresh_token_jwt(sub: str, refresh_token_id: str):
    """Create a JWT that references a refresh token stored in the database"""
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "iat": now,
        "exp": now + (REFRESH_TOKEN_EXP_DAYS * 24 * 60 * 60),  # Convert days to seconds
        "iss": "potato-price-api",
        "type": "refresh",
        "jti": refresh_token_id,  # JWT ID points to the refresh token in DB
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token


def decode_access_token(token: str):
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALG],
        options={"require": ["exp", "iat", "sub"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_refresh_token(token: str):
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALG],
        options={"require": ["exp", "iat", "sub", "jti"]},
    )
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def get_refresh_token_expiry():
    """Get the expiry date for new refresh tokens"""
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXP_DAYS)
