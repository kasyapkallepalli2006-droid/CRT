import datetime
from bson import ObjectId
from bson.errors import InvalidId
from database.connections import db
from utils.file_helper import save_file, delete_file

def is_valid_object_id(id_string):
    try:
        ObjectId(id_string)
        return True
    except (InvalidId, Exception):
        return False

def upload_file_to_complaint(complaint_id, file, current_user):
    """
    Attaches an uploaded file to a specific complaint.

    Steps:
    1. Validate complaint exists and user owns it
    2. Check attachment limit (max 3 files per complaint)
    3. Save file to disk
    4. Store file metadata in complaint document
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    is_owner = str(complaint['user_id']) == str(current_user['_id'])
    is_admin = current_user.get('role') == 'admin'

    if not is_owner and not is_admin:
        return False, "You can only upload files to your own complaints", 403

    current_attachments = complaint.get('attachments', [])
    if len(current_attachments) >= 3:
        return False, "Maximum 3 files allowed per complaint", 400

    success, result = save_file(file)

    if not success:
        return False, result, 400

    filename = result

    attachment = {
        "filename": filename,
        "original_name": file.filename,  
        "filepath": f"uploads/{filename}",
        "uploaded_by": current_user['_id'],
        "uploaded_at": datetime.datetime.utcnow()
    }

    db.complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {
            "$push": {"attachments": attachment},
            "$set": {"updated_at": datetime.datetime.utcnow()}
        }
    )

    return True, {
        "message": "File uploaded successfully",
        "filename": filename,
        "original_name": file.filename,
        "filepath": f"uploads/{filename}"
    }, 201

def get_complaint_files(complaint_id, current_user):
    """
    Returns list of all files attached to a complaint.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    is_owner = str(complaint['user_id']) == str(current_user['_id'])
    is_admin = current_user.get('role') == 'admin'

    if not is_owner and not is_admin:
        return False, "Not authorized to view these files", 403

    attachments = []
    for att in complaint.get('attachments', []):
        attachments.append({
            "filename": att['filename'],
            "original_name": att.get('original_name', att['filename']),
            "filepath": att['filepath'],
            "uploaded_at": str(att.get('uploaded_at', ''))
        })

    return True, {
        "complaint_id": complaint['complaint_id'],
        "total_files": len(attachments),
        "attachments": attachments
    }, 200

def delete_file_from_complaint(complaint_id, filename, current_user):
    """
    Removes a file from a complaint.
    Deletes from both disk AND MongoDB attachment array.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    is_owner = str(complaint['user_id']) == str(current_user['_id'])
    is_admin = current_user.get('role') == 'admin'

    if not is_owner and not is_admin:
        return False, "Not authorized to delete this file", 403

    attachments = complaint.get('attachments', [])
    file_exists = any(att['filename'] == filename for att in attachments)

    if not file_exists:
        return False, "File not found in this complaint", 404

    success, message = delete_file(filename)
    if not success:
        return False, message, 400

    db.complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {
            "$pull": {"attachments": {"filename": filename}},
            "$set": {"updated_at": datetime.datetime.utcnow()}
        }
    )

    return True, {"message": "File deleted successfully"}, 200