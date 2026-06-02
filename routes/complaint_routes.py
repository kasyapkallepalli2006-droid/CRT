# routes/complaint_routes.py
from flask import Blueprint, request
from middleware.auth_middleware import token_required, admin_required
from services.complaint_service import (
    create_complaint,
    get_user_complaints,
    get_complaint_by_id,
    update_complaint,
    delete_complaint,
    get_all_complaints_filtered,
    admin_update_status,
    escalate_complaint
)
from utils.response_helper import success_response, error_response

complaint_bp = Blueprint('complaints', __name__)


@complaint_bp.route('/complaints', methods=['POST'])
@token_required
def create(current_user):
    """
    Submit a new complaint.
    ---
    tags:
      - Complaints
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - description
            - category
          properties:
            title:
              type: string
              example: Street light broken near bus stand
              description: Minimum 10 characters
            description:
              type: string
              example: The street light near Gandhi Bus Stand has been broken for 3 weeks causing safety issues at night.
              description: Minimum 20 characters
            category:
              type: string
              example: Electricity
              enum: [Infrastructure, Electricity, Water, Internet, Transport, Service Issue, Others]
            priority:
              type: string
              example: High
              enum: [Low, Medium, High, Critical]
    responses:
      201:
        description: Complaint submitted successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                complaint_id:
                  type: string
                  example: CMP-2024-0001
                id:
                  type: string
                  example: 64f1a2b3c4d5e6f7a8b9c0d1
      400:
        description: Validation error
      401:
        description: Token missing or invalid
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("No data provided")
    success, result, code = create_complaint(data, current_user)
    if success:
        return success_response("Complaint submitted successfully", result, code)
    return error_response(result, code)


@complaint_bp.route('/complaints', methods=['GET'])
@token_required
def get_mine(current_user):
    """
    Get all complaints submitted by logged-in user.
    ---
    tags:
      - Complaints
    security:
      - Bearer: []
    responses:
      200:
        description: Complaints fetched successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                count:
                  type: integer
                  example: 3
                complaints:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                      complaint_id:
                        type: string
                        example: CMP-2024-0001
                      title:
                        type: string
                      category:
                        type: string
                      priority:
                        type: string
                      status:
                        type: string
      401:
        description: Token missing or invalid
    """
    success, result, code = get_user_complaints(current_user)
    return success_response("Complaints fetched", result, code)


@complaint_bp.route('/complaints/<complaint_id>', methods=['GET'])
@token_required
def get_one(current_user, complaint_id):
    """
    Get a single complaint by ID.
    ---
    tags:
      - Complaints
    security:
      - Bearer: []
    parameters:
      - in: path
        name: complaint_id
        required: true
        type: string
        description: MongoDB ObjectId of the complaint
        example: 64f1a2b3c4d5e6f7a8b9c0d1
    responses:
      200:
        description: Complaint fetched successfully
      400:
        description: Invalid complaint ID format
      403:
        description: Not authorized to view this complaint
      404:
        description: Complaint not found
    """
    success, result, code = get_complaint_by_id(complaint_id, current_user)
    if success:
        return success_response("Complaint fetched", result, code)
    return error_response(result, code)


@complaint_bp.route('/complaints/<complaint_id>', methods=['PUT'])
@token_required
def update(current_user, complaint_id):
    """
    Update own complaint. Only allowed when status is Pending.
    ---
    tags:
      - Complaints
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
          properties:
            title:
              type: string
              example: Updated complaint title here
            description:
              type: string
              example: Updated description with more details about the issue
            category:
              type: string
              example: Water
              enum: [Infrastructure, Electricity, Water, Internet, Transport, Service Issue, Others]
            priority:
              type: string
              example: Critical
              enum: [Low, Medium, High, Critical]
    responses:
      200:
        description: Complaint updated successfully
      400:
        description: Cannot edit — status is not Pending
      403:
        description: Can only edit own complaints
      404:
        description: Complaint not found
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("No data provided")
    success, result, code = update_complaint(complaint_id, data, current_user)
    if success:
        return success_response(result['message'], None, code)
    return error_response(result, code)


@complaint_bp.route('/complaints/<complaint_id>', methods=['DELETE'])
@token_required
def delete(current_user, complaint_id):
    """
    Delete own complaint. Only allowed when status is Pending.
    ---
    tags:
      - Complaints
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
        description: Complaint deleted successfully
      400:
        description: Cannot delete — status is not Pending
      403:
        description: Can only delete own complaints
      404:
        description: Complaint not found
    """
    success, result, code = delete_complaint(complaint_id, current_user)
    if success:
        return success_response(result['message'], None, code)
    return error_response(result, code)


@complaint_bp.route('/admin/complaints', methods=['GET'])
@token_required
@admin_required
def admin_get_all(current_user):
    """
    Get ALL complaints in the system. Admin only.
    ---
    tags:
      - Admin - Complaints
    security:
      - Bearer: []
    parameters:
      - in: query
        name: status
        type: string
        enum: [Pending, Assigned, In Progress, Escalated, Resolved, Closed]
        description: Filter by status
      - in: query
        name: category
        type: string
        enum: [Infrastructure, Electricity, Water, Internet, Transport, Service Issue, Others]
        description: Filter by category
      - in: query
        name: priority
        type: string
        enum: [Low, Medium, High, Critical]
        description: Filter by priority
    responses:
      200:
        description: All complaints fetched successfully
      403:
        description: Admin access required
    """
    filters = {
        "status": request.args.get('status'),
        "category": request.args.get('category'),
        "priority": request.args.get('priority')
    }
    success, result, code = get_all_complaints_filtered(filters)
    return success_response("All complaints fetched", result, code)


@complaint_bp.route('/admin/complaints/<complaint_id>/status', methods=['PUT'])
@token_required
@admin_required
def update_status(current_user, complaint_id):
    """
    Update complaint status. Admin only. Enforces workflow transitions.
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
            - status
          properties:
            status:
              type: string
              example: Assigned
              enum: [Pending, Assigned, In Progress, Escalated, Resolved, Closed]
              description: >
                Allowed transitions:
                Pending → Assigned,
                Assigned → In Progress,
                In Progress → Resolved or Escalated,
                Escalated → In Progress,
                Resolved → Closed
            note:
              type: string
              example: Team assigned to investigate the issue
            assigned_to:
              type: string
              example: 64f1a2b3c4d5e6f7a8b9c0d1
              description: Admin user ID (required when status is Assigned)
    responses:
      200:
        description: Status updated successfully
      400:
        description: Invalid status transition
      403:
        description: Admin access required
      404:
        description: Complaint not found
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("No data provided")
    success, result, code = admin_update_status(complaint_id, data, current_user)
    if success:
        return success_response(result['message'], None, code)
    return error_response(result, code)