# api/app/decorators.py
from functools import wraps
from flask import request, jsonify
from .utils.jwt_utils import decode_access_token

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing_token"}), 401
        token = auth.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            request.user = payload.get("sub")
        except Exception as e:
            return jsonify({"error": "invalid_token", "details": str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper
