import datetime
from bson import ObjectId
from bson.errors import InvalidId
from database.connections import db
from models.complaint_model import (
    create_complaint_document,
    create_status_history_entry,
    VALID_STATUSES,
    VALID_PRIORITIES,
    VALID_CATEGORIES,
    ALLOWED_TRANSITIONS
)

def generate_complaint_id():
    """
    Generates human-readable IDs like CMP-2024-0001

    How it works:
    1. Count existing complaints in DB
    2. Increment by 1
    3. Format with year and zero-padded number
    """
    year = datetime.datetime.utcnow().year
    count = db.complaints.count_documents({})
    number = str(count + 1).zfill(4)  # zfill pads with zeros: 1 → 0001
    return f"CMP-{year}-{number}"


def format_complaint(complaint):
    """
    Converts MongoDB complaint document to JSON-safe dictionary.
    ObjectId fields must be converted to strings for JSON serialization.
    """
    complaint['id'] = str(complaint['_id'])
    del complaint['_id']

    complaint['user_id'] = str(complaint['user_id'])

    if complaint.get('assigned_to'):
        complaint['assigned_to'] = str(complaint['assigned_to'])

    for entry in complaint.get('status_history', []):
        if entry.get('changed_by'):
            entry['changed_by'] = str(entry['changed_by'])
        if entry.get('changed_at'):
            entry['changed_at'] = str(entry['changed_at'])

    for field in ['created_at', 'updated_at', 'resolved_at']:
        if complaint.get(field):
            complaint[field] = str(complaint[field])

    return complaint

def is_valid_object_id(id_string):
    """
    Checks if a string is a valid MongoDB ObjectId format.
    Prevents crashes from invalid IDs in URLs.
    """
    try:
        ObjectId(id_string)
        return True
    except (InvalidId, Exception):
        return False

def create_complaint(data, current_user):
    """
    Creates a new complaint.
    Returns (success, response_data, status_code)
    """
    required = ['title', 'description', 'category']
    for field in required:
        if field not in data or not str(data[field]).strip():
            return False, f"Missing or empty required field: {field}", 400

    if data['category'] not in VALID_CATEGORIES:
        return False, f"Invalid category. Allowed: {VALID_CATEGORIES}", 400

    if 'priority' in data and data['priority'] not in VALID_PRIORITIES:
        return False, f"Invalid priority. Allowed: {VALID_PRIORITIES}", 400

    if len(data['title'].strip()) < 10:
        return False, "Title must be at least 10 characters", 400

    # Step 5: Validate description length
    if len(data['description'].strip()) < 20:
        return False, "Description must be at least 20 characters", 400

    # Step 6: Generate human-readable complaint ID
    complaint_id = generate_complaint_id()

    # Step 7: Build document
    complaint_doc = create_complaint_document(
        user_id=current_user['_id'],
        data=data,
        complaint_id=complaint_id
    )

    # Step 8: Insert into MongoDB
    result = db.complaints.insert_one(complaint_doc)

    # Step 9: Create notification for user
    # We'll build the full notification system in Phase 10
    # For now we insert a basic notification directly
    db.notifications.insert_one({
        "user_id": current_user['_id'],
        "complaint_id": result.inserted_id,
        "type": "complaint_created",
        "message": f"Your complaint '{data['title']}' has been submitted successfully. ID: {complaint_id}",
        "is_read": False,
        "created_at": datetime.datetime.utcnow()
    })

    return True, {
        "complaint_id": complaint_id,
        "id": str(result.inserted_id),
        "message": "Complaint submitted successfully"
    }, 201


# ─── GET User's Own Complaints ────────────────────────────────────

def get_user_complaints(current_user):
    """
    Returns all complaints belonging to the logged-in user.
    Users can only see their own complaints.
    """
    complaints = list(db.complaints.find(
        {"user_id": current_user['_id']}
    ).sort("created_at", -1))  # -1 = newest first

    formatted = [format_complaint(c) for c in complaints]

    return True, {
        "count": len(formatted),
        "complaints": formatted
    }, 200


# ─── GET Single Complaint ─────────────────────────────────────────

def get_complaint_by_id(complaint_id, current_user):
    """
    Returns a single complaint by MongoDB _id.
    Users can only view their own complaints.
    Admins can view any complaint.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    # Security check — users can only see their own complaints
    # Admins bypass this check
    is_owner = str(complaint['user_id']) == str(current_user['_id'])
    is_admin = current_user.get('role') == 'admin'

    if not is_owner and not is_admin:
        return False, "You are not authorized to view this complaint", 403

    return True, {"complaint": format_complaint(complaint)}, 200


# ─── UPDATE Complaint (User edits own complaint) ──────────────────

def update_complaint(complaint_id, data, current_user):
    """
    Allows user to edit their own complaint.
    Only allowed when status is still Pending.
    Users cannot change status — only admins can.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    # Only the owner can edit
    if str(complaint['user_id']) != str(current_user['_id']):
        return False, "You can only edit your own complaints", 403

    # Can only edit if still Pending — once assigned, it's in workflow
    if complaint['status'] != 'Pending':
        return False, "Complaint can only be edited when status is Pending", 400

    # Validate category if being changed
    if 'category' in data and data['category'] not in VALID_CATEGORIES:
        return False, f"Invalid category. Allowed: {VALID_CATEGORIES}", 400

    # Validate priority if being changed
    if 'priority' in data and data['priority'] not in VALID_PRIORITIES:
        return False, f"Invalid priority. Allowed: {VALID_PRIORITIES}", 400

    # Build update — only allow these fields to be changed by user
    # Users CANNOT change status, user_id, complaint_id
    update_fields = {}

    if 'title' in data and data['title'].strip():
        update_fields['title'] = data['title'].strip()

    if 'description' in data and data['description'].strip():
        update_fields['description'] = data['description'].strip()

    if 'category' in data:
        update_fields['category'] = data['category']

    if 'priority' in data:
        update_fields['priority'] = data['priority']

    if not update_fields:
        return False, "No valid fields to update", 400

    update_fields['updated_at'] = datetime.datetime.utcnow()

    db.complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": update_fields}
    )

    return True, {"message": "Complaint updated successfully"}, 200


# ─── DELETE Complaint ─────────────────────────────────────────────

def delete_complaint(complaint_id, current_user):
    """
    Deletes a complaint.
    Only allowed when status is Pending.
    Only the owner can delete.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    if str(complaint['user_id']) != str(current_user['_id']):
        return False, "You can only delete your own complaints", 403

    if complaint['status'] != 'Pending':
        return False, "Only Pending complaints can be deleted", 400

    db.complaints.delete_one({"_id": ObjectId(complaint_id)})

    return True, {"message": "Complaint deleted successfully"}, 200


# ─── ADMIN: Get All Complaints ────────────────────────────────────

def admin_get_all_complaints():
    """
    Returns ALL complaints in the system.
    Admin only.
    Supports filtering by status, category, priority via query params.
    """
    # Build filter from query params
    # request is not available here — we receive filters as a dict
    pass  # We handle filtering in the route — see complaint_routes.py


def get_all_complaints_filtered(filters):
    """
    Fetches complaints with optional filters.
    filters is a dict built in the route from request.args
    """
    query = {}

    if filters.get('status'):
        query['status'] = filters['status']

    if filters.get('category'):
        query['category'] = filters['category']

    if filters.get('priority'):
        query['priority'] = filters['priority']

    complaints = list(db.complaints.find(query).sort("created_at", -1))
    formatted = [format_complaint(c) for c in complaints]

    return True, {
        "count": len(formatted),
        "complaints": formatted
    }, 200


# ─── ADMIN: Update Complaint Status ──────────────────────────────

def admin_update_status(complaint_id, data, current_user):
    """
    Admin updates complaint status.
    Enforces valid status transitions from ALLOWED_TRANSITIONS.
    Records every change in status_history.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    if 'status' not in data:
        return False, "New status is required", 400

    new_status = data['status']

    # Validate the new status value
    if new_status not in VALID_STATUSES:
        return False, f"Invalid status. Allowed: {VALID_STATUSES}", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    current_status = complaint['status']

    # Enforce state machine transitions
    allowed_next = ALLOWED_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_next:
        return False, (
            f"Cannot change status from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {allowed_next}"
        ), 400

    # Build history entry
    note = data.get('note', f"Status changed to {new_status}")
    history_entry = create_status_history_entry(
        status=new_status,
        changed_by=current_user['_id'],
        note=note
    )

    # Build the update
    now = datetime.datetime.utcnow()
    update = {
        "$set": {
            "status": new_status,
            "updated_at": now
        },
        # $push appends to the status_history array
        "$push": {
            "status_history": history_entry
        }
    }

    # Set resolved_at if resolving
    if new_status == 'Resolved':
        update['$set']['resolved_at'] = now

    # Handle assigned_to when assigning
    if new_status == 'Assigned' and 'assigned_to' in data:
        if is_valid_object_id(data['assigned_to']):
            update['$set']['assigned_to'] = ObjectId(data['assigned_to'])

    db.complaints.update_one({"_id": ObjectId(complaint_id)}, update)

    # Notify the user about status change
    db.notifications.insert_one({
        "user_id": complaint['user_id'],
        "complaint_id": complaint['_id'],
        "type": "status_updated",
        "message": f"Your complaint {complaint['complaint_id']} status changed to '{new_status}'",
        "is_read": False,
        "created_at": now
    })

    return True, {
        "message": f"Status updated to '{new_status}' successfully"
    }, 200


# ─── ADMIN: Escalate Complaint ────────────────────────────────────

def escalate_complaint(complaint_id, data, current_user):
    """
    Escalates a complaint that is In Progress or unresolved.
    Increments escalation_count and sets is_escalated flag.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    # Only In Progress complaints can be escalated
    if complaint['status'] not in ['In Progress', 'Assigned']:
        return False, "Only 'In Progress' or 'Assigned' complaints can be escalated", 400

    note = data.get('note', 'Complaint escalated due to no resolution')
    now = datetime.datetime.utcnow()

    history_entry = create_status_history_entry(
        status='Escalated',
        changed_by=current_user['_id'],
        note=note
    )

    db.complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {
            "$set": {
                "status": "Escalated",
                "is_escalated": True,
                "updated_at": now
            },
            "$inc": {"escalation_count": 1},  # $inc increments a number field
            "$push": {"status_history": history_entry}
        }
    )

    # Notify the user
    db.notifications.insert_one({
        "user_id": complaint['user_id'],
        "complaint_id": complaint['_id'],
        "type": "escalation_alert",
        "message": f"Your complaint {complaint['complaint_id']} has been escalated for priority resolution",
        "is_read": False,
        "created_at": now
    })

    return True, {
        "message": "Complaint escalated successfully",
        "escalation_count": complaint['escalation_count'] + 1
    }, 200