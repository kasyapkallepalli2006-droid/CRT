# routes/auth_routes.py
from flask import Blueprint, request, jsonify
from services.auth_service import register_user, login_user
from middleware.auth_middleware import token_required, admin_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - password
          properties:
            name:
              type: string
              example: Arjun Kumar
            email:
              type: string
              example: arjun@email.com
            password:
              type: string
              example: pass1234
            phone:
              type: string
              example: "9876543210"
            role:
              type: string
              example: user
              enum: [user, admin]
    responses:
      201:
        description: Registration successful
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Registration successful
            user_id:
              type: string
              example: 64f1a2b3c4d5e6f7a8b9c0d1
      400:
        description: Missing fields or invalid data
      409:
        description: Email already registered
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "fail", "error": "No data provided"}), 400
    success, response, status_code = register_user(data)
    if success:
        return jsonify({"status": "success", **response}), status_code
    return jsonify({"status": "fail", **response}), status_code


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login and receive a JWT token.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: arjun@email.com
            password:
              type: string
              example: pass1234
    responses:
      200:
        description: Login successful — returns JWT token
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            token:
              type: string
              example: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
            user:
              type: object
              properties:
                id:
                  type: string
                name:
                  type: string
                  example: Arjun Kumar
                email:
                  type: string
                  example: arjun@email.com
                role:
                  type: string
                  example: user
      400:
        description: Missing required fields
      401:
        description: Invalid email or password
      403:
        description: Account is disabled
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "fail", "error": "No data provided"}), 400
    success, response, status_code = login_user(data)
    if success:
        return jsonify({"status": "success", **response}), status_code
    return jsonify({"status": "fail", **response}), status_code


@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """
    Get logged-in user's own profile.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Profile fetched successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                user:
                  type: object
                  properties:
                    id:
                      type: string
                    name:
                      type: string
                      example: Arjun Kumar
                    email:
                      type: string
                      example: arjun@email.com
                    role:
                      type: string
                      example: user
                    created_at:
                      type: string
      401:
        description: Token missing or invalid
    """
    return jsonify({
        "status": "success",
        "data": {
            "user": {
                "id": str(current_user['_id']),
                "name": current_user['name'],
                "email": current_user['email'],
                "role": current_user['role'],
                "created_at": str(current_user['created_at'])
            }
        }
    }), 200


@auth_bp.route('/admin/dashboard', methods=['GET'])
@token_required
@admin_required
def admin_dashboard(current_user):
    """
    Admin dashboard welcome route.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Admin access confirmed
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Welcome Admin User
      401:
        description: Token missing or invalid
      403:
        description: Admin access required
    """
    return jsonify({
        "status": "success",
        "message": f"Welcome Admin {current_user['name']}",
        "role": current_user['role']
    }), 200