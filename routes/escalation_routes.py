# routes/escalation_routes.py
from flask import Blueprint, request
from middleware.auth_middleware import token_required, admin_required
from services.escalation_service import (
    manual_escalate,
    de_escalate,
    auto_escalate_stale_complaints,
    get_escalated_complaints,
    get_escalation_history
)
from utils.response_helper import success_response, error_response

escalation_bp = Blueprint('escalation', __name__)


@escalation_bp.route(
    '/admin/complaints/<complaint_id>/escalate',
    methods=['POST']
)
@token_required
@admin_required
def escalate(current_user, complaint_id):
    """
    Manually escalate a complaint. Admin only.
    ---
    tags:
      - Escalation
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
        schema:
          type: object
          properties:
            note:
              type: string
              example: No progress for 5 days — escalating to senior team
    responses:
      200:
        description: Complaint escalated successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                escalation_count:
                  type: integer
                  example: 1
                escalated_by:
                  type: string
                  example: Admin User
      400:
        description: Complaint not in escalatable status
      404:
        description: Complaint not found
    """
    data = request.get_json(silent=True) or {}
    success, result, code = manual_escalate(complaint_id, data, current_user)
    if success:
        return success_response(result['message'], result, code)
    return error_response(result, code)


@escalation_bp.route(
    '/admin/complaints/<complaint_id>/de-escalate',
    methods=['POST']
)
@token_required
@admin_required
def de_escalate_complaint(current_user, complaint_id):
    """
    De-escalate a complaint back to In Progress. Admin only.
    ---
    tags:
      - Escalation
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
        schema:
          type: object
          properties:
            note:
              type: string
              example: Escalation handled — resuming resolution process
    responses:
      200:
        description: Complaint de-escalated successfully
      400:
        description: Complaint is not in Escalated status
      404:
        description: Complaint not found
    """
    data = request.get_json(silent=True) or {}
    success, result, code = de_escalate(complaint_id, data, current_user)
    if success:
        return success_response(result['message'], result, code)
    return error_response(result, code)


@escalation_bp.route('/admin/escalation/auto-run', methods=['POST'])
@token_required
@admin_required
def auto_escalate(current_user):
    """
    Auto-escalate all stale complaints (unchanged for 3+ days). Admin only.
    ---
    tags:
      - Escalation
    security:
      - Bearer: []
    responses:
      200:
        description: Auto-escalation completed
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                escalated_count:
                  type: integer
                  example: 3
                escalated_complaints:
                  type: array
                  items:
                    type: string
                  example: [CMP-2024-0001, CMP-2024-0002]
      403:
        description: Admin access required
    """
    success, result, code = auto_escalate_stale_complaints(current_user)
    return success_response(result['message'], result, code)


@escalation_bp.route('/admin/escalation/active', methods=['GET'])
@token_required
@admin_required
def view_escalated(current_user):
    """
    Get all currently escalated complaints. Admin only.
    ---
    tags:
      - Escalation
    security:
      - Bearer: []
    responses:
      200:
        description: Escalated complaints fetched
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                count:
                  type: integer
                complaints:
                  type: array
                  items:
                    type: object
                    properties:
                      complaint_id:
                        type: string
                        example: CMP-2024-0001
                      escalation_count:
                        type: integer
                        example: 2
      403:
        description: Admin access required
    """
    success, result, code = get_escalated_complaints()
    return success_response("Escalated complaints fetched", result, code)


@escalation_bp.route(
    '/admin/complaints/<complaint_id>/escalation-history',
    methods=['GET']
)
@token_required
@admin_required
def escalation_history(current_user, complaint_id):
    """
    Get full escalation history of a complaint. Admin only.
    ---
    tags:
      - Escalation
    security:
      - Bearer: []
    parameters:
      - in: path
        name: complaint_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: Escalation history fetched
      400:
        description: Invalid complaint ID
      404:
        description: Complaint not found
    """
    success, result, code = get_escalation_history(complaint_id)
    if success:
        return success_response("Escalation history fetched", result, code)
    return error_response(result, code)