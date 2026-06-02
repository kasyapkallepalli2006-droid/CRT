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

def create_notification(user_id, complaint_id, notif_type, message):
    """
    Inserts a notification document into the notifications collection.
    Centralized here so escalation always notifies consistently.
    """
    db.notifications.insert_one({
        "user_id": user_id,
        "complaint_id": complaint_id,
        "type": notif_type,
        "message": message,
        "is_read": False,
        "created_at": datetime.datetime.utcnow()
    })

def build_history_entry(status, changed_by, note):
    return {
        "status": status,
        "changed_by": changed_by,
        "note": note,
        "changed_at": datetime.datetime.utcnow()
    }

def manual_escalate(complaint_id, data, current_admin):
    """
    Admin manually escalates a specific complaint.

    Business rules enforced:
    - Complaint must exist
    - Must be in Assigned or In Progress status
    - Records full escalation history
    - Notifies complaint owner
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    allowed_for_escalation = ['Assigned', 'In Progress']
    if complaint['status'] not in allowed_for_escalation:
        return False, (
            f"Only complaints with status {allowed_for_escalation} "
            f"can be escalated. Current status: '{complaint['status']}'"
        ), 400

    note = data.get(
        'note',
        'Complaint escalated due to insufficient progress'
    )

    now = datetime.datetime.utcnow()
    history_entry = build_history_entry(
        status='Escalated',
        changed_by=current_admin['_id'],
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
            "$inc": {"escalation_count": 1},
            "$push": {"status_history": history_entry}
        }
    )
    create_notification(
        user_id=complaint['user_id'],
        complaint_id=complaint['_id'],
        notif_type="escalation_alert",
        message=(
            f"Your complaint '{complaint['complaint_id']}' has been "
            f"escalated for priority attention. Our senior team has "
            f"been notified and will act immediately."
        )
    )
    new_count = complaint['escalation_count'] + 1

    return True, {
        "message": "Complaint escalated successfully",
        "complaint_id": complaint['complaint_id'],
        "escalation_count": new_count,
        "escalated_by": current_admin['name'],
        "note": note
    }, 200

def de_escalate(complaint_id, data, current_admin):
    """
    After handling an escalated complaint, admin moves it
    back to In Progress to continue resolution.

    This is the natural next step after escalation is addressed.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404

    if complaint['status'] != 'Escalated':
        return False, (
            f"Only 'Escalated' complaints can be de-escalated. "
            f"Current status: '{complaint['status']}'"
        ), 400

    note = data.get(
        'note',
        'Escalation addressed — resuming resolution process'
    )

    now = datetime.datetime.utcnow()

    history_entry = build_history_entry(
        status='In Progress',
        changed_by=current_admin['_id'],
        note=note
    )

    db.complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {
            "$set": {
                "status": "In Progress",
                "updated_at": now
            },
            "$push": {"status_history": history_entry}
        }
    )
    create_notification(
        user_id=complaint['user_id'],
        complaint_id=complaint['_id'],
        notif_type="status_updated",
        message=(
            f"Your escalated complaint '{complaint['complaint_id']}' "
            f"is now being actively handled by our senior team."
        )
    )

    return True, {
        "message": "Complaint de-escalated and back to In Progress",
        "complaint_id": complaint['complaint_id']
    }, 200

def auto_escalate_stale_complaints(current_admin):
    """
    Automatically escalates complaints that have been
    Assigned or In Progress for more than 3 days without update.

    In production this would be run by a scheduler (like Celery or APScheduler).
    Here we expose it as an admin-triggered endpoint.

    How it works:
    1. Find all complaints with status Assigned or In Progress
    2. Check if updated_at is older than 3 days
    3. Escalate each one automatically
    4. Return a summary of what was escalated
    """
    three_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=3)

    stale_complaints = list(db.complaints.find({
        "status": {"$in": ["Assigned", "In Progress"]},
        "updated_at": {"$lt": three_days_ago}
    }))

    if not stale_complaints:
        return True, {
            "message": "No stale complaints found",
            "escalated_count": 0,
            "escalated_complaints": []
        }, 200

    escalated_ids = []
    now = datetime.datetime.utcnow()

    for complaint in stale_complaints:
        history_entry = build_history_entry(
            status='Escalated',
            changed_by=current_admin['_id'],
            note=f"Auto-escalated: no progress for 3+ days"
        )

        db.complaints.update_one(
            {"_id": complaint['_id']},
            {
                "$set": {
                    "status": "Escalated",
                    "is_escalated": True,
                    "updated_at": now
                },
                "$inc": {"escalation_count": 1},
                "$push": {"status_history": history_entry}
            }
        )
        create_notification(
            user_id=complaint['user_id'],
            complaint_id=complaint['_id'],
            notif_type="escalation_alert",
            message=(
                f"Your complaint '{complaint['complaint_id']}' has been "
                f"automatically escalated due to no resolution in 3 days. "
                f"Our senior team will now prioritize this."
            )
        )

        escalated_ids.append(complaint['complaint_id'])

    return True, {
        "message": "Auto-escalation completed",
        "escalated_count": len(escalated_ids),
        "escalated_complaints": escalated_ids
    }, 200

def get_escalated_complaints():
    """
    Returns all currently escalated complaints.
    Admin uses this to see what needs immediate attention.
    Sorted by escalation_count descending — most escalated first.
    """
    escalated = list(db.complaints.find(
        {"is_escalated": True, "status": "Escalated"}
    ).sort("escalation_count", -1))

    if not escalated:
        return True, {
            "message": "No escalated complaints",
            "count": 0,
            "complaints": []
        }, 200

    formatted = []
    for c in escalated:
        formatted.append({
            "id": str(c['_id']),
            "complaint_id": c['complaint_id'],
            "title": c['title'],
            "category": c['category'],
            "priority": c['priority'],
            "status": c['status'],
            "escalation_count": c['escalation_count'],
            "user_id": str(c['user_id']),
            "updated_at": str(c['updated_at']),
            "created_at": str(c['created_at'])
        })

    return True, {
        "count": len(formatted),
        "complaints": formatted
    }, 200

def get_escalation_history(complaint_id):
    """
    Returns the full status history of a complaint,
    filtered to show only escalation-related entries.
    Useful for understanding the escalation timeline.
    """
    if not is_valid_object_id(complaint_id):
        return False, "Invalid complaint ID format", 400

    complaint = db.complaints.find_one({"_id": ObjectId(complaint_id)})

    if not complaint:
        return False, "Complaint not found", 404
    escalation_entries = [
        {
            "status": entry['status'],
            "changed_by": str(entry['changed_by']),
            "note": entry.get('note', ''),
            "changed_at": str(entry['changed_at'])
        }
        for entry in complaint.get('status_history', [])
        if entry['status'] == 'Escalated'
    ]

    return True, {
        "complaint_id": complaint['complaint_id'],
        "title": complaint['title'],
        "current_status": complaint['status'],
        "total_escalations": complaint['escalation_count'],
        "escalation_history": escalation_entries
    }, 200