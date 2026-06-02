import jwt
from functools import wraps
from flask import request, jsonify
from services.auth_service import decode_token
from database.connections import db
from bson import ObjectId


def token_required(f):
    @wraps(f)  
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                "status": "fail",
                "error": "Authorization token is missing"
            }), 401

        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                "status": "fail",
                "error": "Invalid token format. Use: Bearer <token>"
            }), 401

        token = parts[1]

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({
                "status": "fail",
                "error": "Token has expired. Please login again"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "status": "fail",
                "error": "Invalid token"
            }), 401
        user = db.users.find_one({"_id": ObjectId(payload['user_id'])})

        if not user:
            return jsonify({
                "status": "fail",
                "error": "User no longer exists"
            }), 401

        if not user.get('is_active', True):
            return jsonify({
                "status": "fail",
                "error": "Account is disabled"
            }), 403
        return f(current_user=user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = kwargs.get('current_user')

        if not current_user or current_user.get('role') != 'admin':
            return jsonify({
                "status": "fail",
                "error": "Admin access required"
            }), 403

        return f(*args, **kwargs)
    return decorated