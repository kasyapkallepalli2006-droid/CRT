from flask import Blueprint, request
from middleware.auth_middleware import token_required
from services.notification_service import (
    get_all_notifications,
    get_unread_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
    get_notifications_by_type
)
from utils.response_helper import success_response, error_response

notification_bp = Blueprint('notifications', __name__)


@notification_bp.route('/notifications', methods=['GET'])
@token_required
def get_all(current_user):
    """
    Get all notifications for logged-in user.
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - in: query
        name: type
        type: string
        enum: [complaint_created, status_updated, complaint_assigned, escalation_alert, complaint_resolved, complaint_closed]
        description: Filter notifications by type
    responses:
      200:
        description: Notifications fetched successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                total:
                  type: integer
                  example: 5
                unread:
                  type: integer
                  example: 3
                read:
                  type: integer
                  example: 2
                notifications:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                      type:
                        type: string
                        example: status_updated
                      message:
                        type: string
                      is_read:
                        type: boolean
                      created_at:
                        type: string
      401:
        description: Token missing or invalid
    """
    notif_type = request.args.get('type')
    if notif_type:
        success, result, code = get_notifications_by_type(
            notif_type, current_user
        )
    else:
        success, result, code = get_all_notifications(current_user)
    if success:
        return success_response("Notifications fetched", result, code)
    return error_response(result, code)


@notification_bp.route('/notifications/unread', methods=['GET'])
@token_required
def get_unread(current_user):
    """
    Get only unread notifications.
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: Unread notifications fetched
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                unread_count:
                  type: integer
                  example: 3
                notifications:
                  type: array
                  items:
                    type: object
      401:
        description: Token missing or invalid
    """
    success, result, code = get_unread_notifications(current_user)
    return success_response("Unread notifications fetched", result, code)


@notification_bp.route('/notifications/count', methods=['GET'])
@token_required
def unread_count(current_user):
    """
    Get unread notification count for badge display.
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: Unread count fetched
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                unread_count:
                  type: integer
                  example: 3
      401:
        description: Token missing or invalid
    """
    success, result, code = get_unread_count(current_user)
    return success_response("Unread count fetched", result, code)


@notification_bp.route('/notifications/read-all', methods=['PUT'])
@token_required
def read_all(current_user):
    """
    Mark all notifications as read.
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    responses:
      200:
        description: All notifications marked as read
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                updated_count:
                  type: integer
                  example: 3
      401:
        description: Token missing or invalid
    """
    success, result, code = mark_all_as_read(current_user)
    return success_response(result['message'], result, code)


@notification_bp.route(
    '/notifications/<notification_id>/read',
    methods=['PUT']
)
@token_required
def read_one(current_user, notification_id):
    """
    Mark a single notification as read.
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - in: path
        name: notification_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: Notification marked as read
      403:
        description: Not your notification
      404:
        description: Notification not found
    """
    success, result, code = mark_as_read(notification_id, current_user)
    if success:
        return success_response(result['message'], None, code)
    return error_response(result, code)


@notification_bp.route(
    '/notifications/<notification_id>',
    methods=['DELETE']
)
@token_required
def delete(current_user, notification_id):
    """
    Delete a notification permanently.
    ---
    tags:
      - Notifications
    security:
      - Bearer: []
    parameters:
      - in: path
        name: notification_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: Notification deleted successfully
      403:
        description: Not your notification
      404:
        description: Notification not found
    """
    success, result, code = delete_notification(notification_id, current_user)
    if success:
        return success_response(result['message'], None, code)
    return error_response(result, code)