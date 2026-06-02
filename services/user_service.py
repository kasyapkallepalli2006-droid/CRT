import datetime
from bson import ObjectId
from bson.errors import InvalidId
from database.connections import db

def format_user(user):
    """
    Converts MongoDB user document to JSON-safe dict.
    Removes sensitive fields before sending to client.
    """
    return {
        "id": str(user['_id']),
        "name": user['name'],
        "email": user['email'],
        "role": user['role'],
        "phone": user.get('phone'),
        "is_active": user.get('is_active', True),
        "created_at": str(user.get('created_at', ''))
    }

def is_valid_object_id(id_string):
    try:
        ObjectId(id_string)
        return True
    except (InvalidId, Exception):
        return False


def get_own_profile(current_user):
    """
    Returns the logged-in user's profile.
    Any authenticated user can call this.
    """
    return True, {"user": format_user(current_user)}, 200


def get_own_stats(current_user):
    """
    Returns complaint statistics for the logged-in user.
    Lets users track their own complaint history at a glance.
    """
    user_id = current_user['_id']

    statuses = ['Pending', 'Assigned', 'In Progress',
                'Escalated', 'Resolved', 'Closed']

    stats = {}
    for status in statuses:
        count = db.complaints.count_documents({
            "user_id": user_id,
            "status": status
        })
        stats[status.lower().replace(' ', '_')] = count
    total = db.complaints.count_documents({"user_id": user_id})

    unread = db.notifications.count_documents({
        "user_id": user_id,
        "is_read": False
    })

    return True, {
        "total_complaints": total,
        "by_status": stats,
        "unread_notifications": unread
    }, 200


def admin_get_all_users():
    """
    Returns all registered users.
    Admin only.
    """
    users = list(db.users.find().sort("created_at", -1))
    formatted = [format_user(u) for u in users]

    return True, {
        "count": len(formatted),
        "users": formatted
    }, 200


def admin_get_user(user_id):
    """
    Returns a single user's profile plus their complaint summary.
    Admin only.
    """
    if not is_valid_object_id(user_id):
        return False, "Invalid user ID format", 400

    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return False, "User not found", 404

    total = db.complaints.count_documents({"user_id": ObjectId(user_id)})
    resolved = db.complaints.count_documents({
        "user_id": ObjectId(user_id),
        "status": "Resolved"
    })
    pending = db.complaints.count_documents({
        "user_id": ObjectId(user_id),
        "status": "Pending"
    })

    return True, {
        "user": format_user(user),
        "complaint_summary": {
            "total": total,
            "resolved": resolved,
            "pending": pending
        }
    }, 200

def admin_toggle_user_status(user_id, current_admin):
    """
    Enables or disables a user account.
    Admin cannot disable their own account.
    Admin cannot disable another admin (safety rule).
    """
    if not is_valid_object_id(user_id):
        return False, "Invalid user ID format", 400

    if str(current_admin['_id']) == user_id:
        return False, "You cannot disable your own account", 400

    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return False, "User not found", 404

    if user.get('role') == 'admin':
        return False, "Cannot disable another admin account", 403

    new_status = not user.get('is_active', True)

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "is_active": new_status,
            "updated_at": datetime.datetime.utcnow()
        }}
    )

    status_text = "enabled" if new_status else "disabled"

    return True, {
        "message": f"User account {status_text} successfully",
        "user_id": user_id,
        "is_active": new_status
    }, 200



def admin_promote_user(user_id, current_admin):
    """
    Promotes a regular user to admin role.
    Cannot demote an existing admin through this endpoint.
    """
    if not is_valid_object_id(user_id):
        return False, "Invalid user ID format", 400

    if str(current_admin['_id']) == user_id:
        return False, "You are already an admin", 400

    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return False, "User not found", 404

    if user.get('role') == 'admin':
        return False, "User is already an admin", 400

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "role": "admin",
            "updated_at": datetime.datetime.utcnow()
        }}
    )

    return True, {
        "message": f"User '{user['name']}' promoted to admin successfully",
        "user_id": user_id
    }, 200

def admin_assign_complaint(complaint_id, data, current_admin):
    """
    Assigns a complaint to a specific admin user.
    The assigned admin is responsible for resolution.
    Separate from status update — assignment is its own action.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    if 'admin_id' not in data:
        return False, "admin_id is required", 400

    if not is_valid_object_id(data['admin_id']):
        return False, "Invalid admin_id format", 400

    assigned_admin = db.users.find_one({
        "_id": ObjectId(data['admin_id']),
        "role": "admin"
    })

    if not assigned_admin:
        return False, "Assigned user not found or is not an admin", 404

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    if complaint['status'] in ['Resolved', 'Closed']:
        return False, "Cannot assign a resolved or closed complaint", 400

    now = datetime.datetime.utcnow()

    db.complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {
            "$set": {
                "assigned_to": ObjectId(data['admin_id']),
                "updated_at": now
            }
        }
    )

    db.notifications.insert_one({
        "user_id": complaint['user_id'],
        "complaint_id": complaint['_id'],
        "type": "complaint_assigned",
        "message": (
            f"Your complaint {complaint['complaint_id']} "
            f"has been assigned to {assigned_admin['name']}"
        ),
        "is_read": False,
        "created_at": now
    })
    return True, {
        "message": f"Complaint assigned to {assigned_admin['name']} successfully",
        "assigned_to": {
            "id": str(assigned_admin['_id']),
            "name": assigned_admin['name'],
            "email": assigned_admin['email']
        }
    }, 200