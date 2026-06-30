from flask import Blueprint, request, send_from_directory, jsonify
from database.connections import db
from middleware.auth_middleware import token_required
from services.upload_service import (
    upload_file_to_complaint,
    get_complaint_files,
    delete_file_from_complaint
)
from utils.response_helper import success_response, error_response
from config import Config

upload_bp = Blueprint('uploads', __name__)


@upload_bp.route('/complaints/<complaint_id>/upload', methods=['POST'])
@token_required
def upload_file(current_user, complaint_id):
    """
    Upload a file attachment to a complaint.
    ---
    tags:
      - Files
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - in: path
        name: complaint_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
      - in: formData
        name: file
        type: file
        required: true
        description: File to upload. Allowed types - jpg, jpeg, png, pdf. Max size - 5MB
    responses:
      201:
        description: File uploaded successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                filename:
                  type: string
                  example: uuid_photo.jpg
                original_name:
                  type: string
                  example: photo.jpg
                filepath:
                  type: string
                  example: uploads/uuid_photo.jpg
      400:
        description: No file or invalid file type
      403:
        description: Not authorized
      404:
        description: Complaint not found
    """
    if 'file' not in request.files:
        return error_response(
            "No file found. Use form-data with key 'file'"
        )
    file = request.files['file']
    success, result, code = upload_file_to_complaint(
        complaint_id, file, current_user
    )
    if success:
        return success_response("File uploaded successfully", result, code)
    return error_response(result, code)


@upload_bp.route('/complaints/<complaint_id>/files', methods=['GET'])
@token_required
def get_files(current_user, complaint_id):
    """
    Get all files attached to a complaint.
    ---
    tags:
      - Files
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
        description: Files fetched successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                total_files:
                  type: integer
                  example: 2
                attachments:
                  type: array
                  items:
                    type: object
                    properties:
                      filename:
                        type: string
                      original_name:
                        type: string
                      filepath:
                        type: string
      403:
        description: Not authorized
      404:
        description: Complaint not found
    """
    success, result, code = get_complaint_files(complaint_id, current_user)
    if success:
        return success_response("Files fetched", result, code)
    return error_response(result, code)


@upload_bp.route(
    '/complaints/<complaint_id>/files/<filename>',
    methods=['DELETE']
)
@token_required
def delete_file(current_user, complaint_id, filename):
    """
    Delete a file from a complaint.
    ---
    tags:
      - Files
    security:
      - Bearer: []
    parameters:
      - in: path
        name: complaint_id
        required: true
        type: string
        example: 64f1a2b3c4d5e6f7a8b9c0d1
      - in: path
        name: filename
        required: true
        type: string
        example: uuid_photo.jpg
    responses:
      200:
        description: File deleted successfully
      403:
        description: Not authorized
      404:
        description: File or complaint not found
    """
    success, result, code = delete_file_from_complaint(
        complaint_id, filename, current_user
    )
    if success:
        return success_response(result['message'], None, code)
    return error_response(result, code)


@upload_bp.route('/uploads/<filename>', methods=['GET'])
@token_required
def serve_file(current_user, filename):
    """
    View or download an uploaded file.
    ---
    tags:
      - Files
    security:
      - Bearer: []
    parameters:
      - in: path
        name: filename
        required: true
        type: string
        example: uuid_photo.jpg
    responses:
      200:
        description: File served successfully
      404:
        description: File not found
    """
    complaint = db.complaints.find_one({"attachments.filename": filename})
    if not complaint:
        return jsonify({"status": "fail", "error": "File not found or unauthorized"}), 404

    is_owner = str(complaint['user_id']) == str(current_user['_id'])
    is_admin = current_user.get('role') == 'admin'

    if not is_owner and not is_admin:
        return jsonify({"status": "fail", "error": "You are not authorized to view this file"}), 403

    return send_from_directory(Config.UPLOAD_FOLDER, filename)