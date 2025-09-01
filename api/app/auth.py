# api/app/auth.py
from flask import Blueprint, request, jsonify, current_app
from .extensions import db, limiter
from .models import User, RefreshToken
from passlib.hash import bcrypt  # Use bcrypt instead of argon2 to avoid crypt module
from .utils.jwt_utils import (
    create_access_token, 
    create_refresh_token_jwt, 
    decode_refresh_token,
    get_refresh_token_expiry,
    JWT_EXP_SECONDS,
    REFRESH_TOKEN_EXP_DAYS
)
from .schemas import AuthRequest, AuthResponse, RefreshRequest, RefreshResponse
from sqlalchemy.exc import NoResultFound
from datetime import datetime, timezone
import jwt

auth_bp = Blueprint("auth", __name__)

def get_client_info(request):
    """Extract client information for security tracking"""
    return {
        "user_agent": request.headers.get("User-Agent", "")[:512],
        "ip": request.remote_addr
    }

def create_token_pair(user_id: int, client_info: str = None):
    """Create both access and refresh tokens for a user"""
    # Create refresh token in database
    refresh_token_record = RefreshToken(
        token=RefreshToken.generate_token(),
        user_id=user_id,
        expires_at=get_refresh_token_expiry(),
        client_info=client_info
    )
    db.session.add(refresh_token_record)
    db.session.flush()  # Get the ID
    
    # Create JWT tokens
    access_token = create_access_token(sub=user_id)
    refresh_token_jwt = create_refresh_token_jwt(sub=user_id, refresh_token_id=str(refresh_token_record.id))
    
    return access_token, refresh_token_jwt, refresh_token_record

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    body = request.get_json()
    try:
        payload = AuthRequest.model_validate(body)
    except Exception as e:
        return jsonify({"error": "invalid_payload", "details": str(e)}), 400

    if db.session.query(User).filter_by(username=payload.username).first():
        return jsonify({"error": "user_exists"}), 400

    # Use bcrypt instead of argon2 to avoid crypt module deprecation warnings
    pw_hash = bcrypt.hash(payload.password)
    u = User(username=payload.username, password_hash=pw_hash)
    db.session.add(u)
    db.session.commit()
    return jsonify({"status": "ok"}), 201

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    body = request.get_json()
    try:
        payload = AuthRequest.model_validate(body)
    except Exception as e:
        return jsonify({"error": "invalid_payload", "details": str(e)}), 400

    user = db.session.query(User).filter_by(username=payload.username).first()
    if not user:
        return jsonify({"error": "invalid_credentials"}), 401

    # Use bcrypt.verify instead of argon2.verify
    if not bcrypt.verify(payload.password, user.password_hash):
        return jsonify({"error": "invalid_credentials"}), 401

    # Create token pair
    client_info = str(get_client_info(request))
    access_token, refresh_token, refresh_record = create_token_pair(user.id, client_info)
    
    db.session.commit()
    
    response = AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_EXP_SECONDS,
        refresh_expires_in=REFRESH_TOKEN_EXP_DAYS * 24 * 60 * 60  # Convert to seconds
    )
    
    return jsonify(response.model_dump()), 200

@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("20 per minute")
def refresh():
    """Exchange a refresh token for new access and refresh tokens"""
    body = request.get_json()
    try:
        payload = RefreshRequest.model_validate(body)
    except Exception as e:
        return jsonify({"error": "invalid_payload", "details": str(e)}), 400

    try:
        # Decode the refresh token JWT
        token_payload = decode_refresh_token(payload.refresh_token)
        user_id = int(token_payload["sub"])
        refresh_token_id = int(token_payload["jti"])
        
        # Find the refresh token in database
        refresh_record = db.session.query(RefreshToken).filter_by(
            id=refresh_token_id,
            user_id=user_id
        ).first()
        
        if not refresh_record:
            return jsonify({"error": "invalid_refresh_token", "details": "Token not found"}), 401
            
        if not refresh_record.is_valid:
            return jsonify({"error": "invalid_refresh_token", "details": "Token expired or revoked"}), 401
        
        # Update last used timestamp
        refresh_record.last_used_at = datetime.now(timezone.utc)
        
        # Revoke the old refresh token (token rotation)
        refresh_record.revoke()
        
        # Create new token pair
        client_info = str(get_client_info(request))
        access_token, new_refresh_token, new_refresh_record = create_token_pair(user_id, client_info)
        
        db.session.commit()
        
        response = RefreshResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=JWT_EXP_SECONDS,
            refresh_expires_in=REFRESH_TOKEN_EXP_DAYS * 24 * 60 * 60
        )
        
        return jsonify(response.model_dump()), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "invalid_refresh_token", "details": "Token expired"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": "invalid_refresh_token", "details": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Refresh token error: {e}")
        return jsonify({"error": "internal_error", "details": "Token refresh failed"}), 500

@auth_bp.route("/revoke", methods=["POST"])
@limiter.limit("10 per minute")
def revoke():
    """Revoke a refresh token"""
    body = request.get_json()
    try:
        payload = RefreshRequest.model_validate(body)
    except Exception as e:
        return jsonify({"error": "invalid_payload", "details": str(e)}), 400

    try:
        # Decode the refresh token JWT
        token_payload = decode_refresh_token(payload.refresh_token)
        user_id = int(token_payload["sub"])
        refresh_token_id = int(token_payload["jti"])
        
        # Find and revoke the refresh token
        refresh_record = db.session.query(RefreshToken).filter_by(
            id=refresh_token_id,
            user_id=user_id
        ).first()
        
        if refresh_record and not refresh_record.is_revoked:
            refresh_record.revoke()
            db.session.commit()
        
        return jsonify({"status": "ok", "message": "Token revoked"}), 200
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        # Even if token is invalid, we return success for security
        return jsonify({"status": "ok", "message": "Token revoked"}), 200
    except Exception as e:
        current_app.logger.error(f"Token revocation error: {e}")
        return jsonify({"error": "internal_error", "details": "Revocation failed"}), 500

@auth_bp.route("/revoke-all", methods=["POST"])
@limiter.limit("5 per minute")
def revoke_all():
    """Revoke all refresh tokens for a user (logout from all devices)"""
    # This endpoint requires authentication
    from .decorators import jwt_required
    
    @jwt_required
    def _revoke_all():
        user_id = request.user
        
        # Revoke all active refresh tokens for the user
        active_tokens = db.session.query(RefreshToken).filter_by(
            user_id=user_id,
            revoked_at=None
        ).all()
        
        for token in active_tokens:
            token.revoke()
        
        db.session.commit()
        
        return jsonify({
            "status": "ok", 
            "message": f"Revoked {len(active_tokens)} tokens"
        }), 200
    
    return _revoke_all()