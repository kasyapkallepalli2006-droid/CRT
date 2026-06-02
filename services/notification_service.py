import datetime
from bson import ObjectId
from bson.errors import InvalidId
from database.connections import db

def is_valid_object_id(id_string):
    try:
        ObjectId(id_string)
        return True
    except (InvalidId, Exception):
        return False

def format_notification(notification):
    """
    Converts MongoDB notification document to JSON-safe dict.
    ObjectId fields converted to strings.
    """
    return {
        "id": str(notification['_id']),
        "user_id": str(notification['user_id']),
        "complaint_id": str(notification.get('complaint_id', '')),
        "type": notification.get('type', ''),
        "message": notification.get('message', ''),
        "is_read": notification.get('is_read', False),
        "created_at": str(notification.get('created_at', ''))
    }

def get_all_notifications(current_user):
    """
    Returns ALL notifications for the logged-in user.
    Sorted newest first.
    Unread notifications appear with is_read: false.
    """
    notifications = list(db.notifications.find(
        {"user_id": current_user['_id']}
    ).sort("created_at", -1))  # -1 = newest first

    formatted = [format_notification(n) for n in notifications]

    unread_count = sum(1 for n in formatted if not n['is_read'])
    read_count = sum(1 for n in formatted if n['is_read'])

    return True, {
        "total": len(formatted),
        "unread": unread_count,
        "read": read_count,
        "notifications": formatted
    }, 200

def get_unread_notifications(current_user):
    """
    Returns ONLY unread notifications.
    Useful for showing new alerts to the user.
    """
    notifications = list(db.notifications.find(
        {
            "user_id": current_user['_id'],
            "is_read": False
        }
    ).sort("created_at", -1))

    formatted = [format_notification(n) for n in notifications]

    return True, {
        "unread_count": len(formatted),
        "notifications": formatted
    }, 200

def get_unread_count(current_user):
    """
    Returns just the count of unread notifications.
    Used for notification badge (the red number on bell icon).
    Lightweight — no need to fetch full documents.
    """
    count = db.notifications.count_documents({
        "user_id": current_user['_id'],
        "is_read": False
    })

    return True, {"unread_count": count}, 200

def mark_as_read(notification_id, current_user):
    """
    Marks a single notification as read.
    User can only mark their own notifications.
    """
    if not is_valid_object_id(notification_id):
        return False, "Invalid notification ID format", 400

    notification = db.notifications.find_one({
        "_id": ObjectId(notification_id)
    })

    if not notification:
        return False, "Notification not found", 404

    if str(notification['user_id']) != str(current_user['_id']):
        return False, "Not authorized to update this notification", 403

    if notification.get('is_read', False):
        return True, {"message": "Notification already marked as read"}, 200

    db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {
            "$set": {
                "is_read": True,
                "read_at": datetime.datetime.utcnow()
            }
        }
    )

    return True, {"message": "Notification marked as read"}, 200

def mark_all_as_read(current_user):
    """
    Marks ALL unread notifications as read for the logged-in user.
    Common "clear all" action in notification panels.
    """
    now = datetime.datetime.utcnow()

    result = db.notifications.update_many(
        {
            "user_id": current_user['_id'],
            "is_read": False
        },
        {
            "$set": {
                "is_read": True,
                "read_at": now
            }
        }
    )

    updated = result.modified_count

    if updated == 0:
        return True, {
            "message": "No unread notifications to mark",
            "updated_count": 0
        }, 200

    return True, {
        "message": f"{updated} notification(s) marked as read",
        "updated_count": updated
    }, 200

def delete_notification(notification_id, current_user):
    """
    Permanently deletes a single notification.
    User can only delete their own notifications.
    """
    if not is_valid_object_id(notification_id):
        return False, "Invalid notification ID format", 400

    notification = db.notifications.find_one({
        "_id": ObjectId(notification_id)
    })

    if not notification:
        return False, "Notification not found", 404

    if str(notification['user_id']) != str(current_user['_id']):
        return False, "Not authorized to delete this notification", 403

    db.notifications.delete_one({"_id": ObjectId(notification_id)})

    return True, {"message": "Notification deleted successfully"}, 200

def get_notifications_by_type(notif_type, current_user):
    """
    Filters notifications by type.
    Example: get only escalation_alert notifications.

    Valid types:
    complaint_created, status_updated, complaint_assigned,
    escalation_alert, complaint_resolved, complaint_closed
    """
    valid_types = [
        'complaint_created',
        'status_updated',
        'complaint_assigned',
        'escalation_alert',
        'complaint_resolved',
        'complaint_closed'
    ]

    if notif_type not in valid_types:
        return False, f"Invalid type. Valid types: {valid_types}", 400

    notifications = list(db.notifications.find(
        {
            "user_id": current_user['_id'],
            "type": notif_type
        }
    ).sort("created_at", -1))

    formatted = [format_notification(n) for n in notifications]

    return True, {
        "type": notif_type,
        "count": len(formatted),
        "notifications": formatted
    }, 200