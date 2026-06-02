# routes/user_routes.py
from flask import Blueprint, request
from middleware.auth_middleware import token_required, admin_required
from services.user_service import (
    get_own_profile,
    get_own_stats,
    admin_get_all_users,
    admin_get_user,
    admin_toggle_user_status,
    admin_promote_user,
    admin_assign_complaint
)
from utils.response_helper import success_response, error_response

user_bp = Blueprint('users', __name__)


@user_bp.route('/profile', methods=['GET'])
@token_required
def my_profile(current_user):
    """
    Get logged-in user's own profile.
    ---
    tags:
      - Users
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
                    is_active:
                      type: boolean
                      example: true
      401:
        description: Token missing or invalid
    """
    success, result, code = get_own_profile(current_user)
    return success_response("Profile fetched", result, code)


@user_bp.route('/my-stats', methods=['GET'])
@token_required
def my_stats(current_user):
    """
    Get complaint statistics for logged-in user.
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Stats fetched successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                total_complaints:
                  type: integer
                  example: 5
                by_status:
                  type: object
                  properties:
                    pending:
                      type: integer
                      example: 2
                    resolved:
                      type: integer
                      example: 2
                unread_notifications:
                  type: integer
                  example: 3
      401:
        description: Token missing or invalid
    """
    success, result, code = get_own_stats(current_user)
    return success_response("Stats fetched", result, code)


@user_bp.route('/admin/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user):
    """
    Get all registered users. Admin only.
    ---
    tags:
      - Admin - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Users fetched successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                count:
                  type: integer
                  example: 10
                users:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                      name:
                        type: string
                      email:
                        type: string
                      role:
                        type: string
                      is_active:
                        type: boolean
      403:
        description: Admin access required
    """
    success, result, code = admin_get_all_users()
    return success_response("Users fetched", result, code)


@user_bp.route('/admin/users/<user_id>', methods=['GET'])
@token_required
@admin_required
def get_user(current_user, user_id):
    """
    Get a specific user with complaint summary. Admin only.
    ---
    tags:
      - Admin - Users
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: User fetched with complaint summary
      400:
        description: Invalid user ID format
      403:
        description: Admin access required
      404:
        description: User not found
    """
    success, result, code = admin_get_user(user_id)
    if success:
        return success_response("User fetched", result, code)
    return error_response(result, code)


@user_bp.route('/admin/users/<user_id>/toggle-status', methods=['PUT'])
@token_required
@admin_required
def toggle_user(current_user, user_id):
    """
    Enable or disable a user account. Admin only.
    ---
    tags:
      - Admin - Users
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: Account status toggled successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                is_active:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: User account disabled successfully
      400:
        description: Cannot disable your own account
      403:
        description: Cannot disable another admin
      404:
        description: User not found
    """
    success, result, code = admin_toggle_user_status(user_id, current_user)
    if success:
        return success_response(result['message'], result, code)
    return error_response(result, code)


@user_bp.route('/admin/users/<user_id>/promote', methods=['PUT'])
@token_required
@admin_required
def promote_user(current_user, user_id):
    """
    Promote a regular user to admin role. Admin only.
    ---
    tags:
      - Admin - Users
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: User promoted to admin successfully
      400:
        description: User is already an admin
      403:
        description: Admin access required
      404:
        description: User not found
    """
    success, result, code = admin_promote_user(user_id, current_user)
    if success:
        return success_response(result['message'], result, code)
    return error_response(result, code)


@user_bp.route('/admin/complaints/<complaint_id>/assign', methods=['PUT'])
@token_required
@admin_required
def assign_complaint(current_user, complaint_id):
    """
    Assign a complaint to a specific admin. Admin only.
    ---
    tags:
      - Admin - Complaints
    security:
      - Bearer: []
    parameters:
      - in: path
        name: complaint_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - admin_id
          properties:
            admin_id:
              type: string
              example: 64f1a2b3c4d5e6f7a8b9c0d1
              description: MongoDB ObjectId of the admin user
    responses:
      200:
        description: Complaint assigned successfully
      400:
        description: Cannot assign resolved or closed complaint
      404:
        description: Complaint or admin not found
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("No data provided")
    success, result, code = admin_assign_complaint(
        complaint_id, data, current_user
    )
    if success:
        return success_response(result['message'], result, code)
    return error_response(result, code)