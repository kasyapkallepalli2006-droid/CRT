import datetime

VALID_STATUSES = [
    'Pending',
    'Assigned',
    'In Progress',
    'Escalated',
    'Resolved',
    'Closed'
]

VALID_PRIORITIES = [
    'Low',
    'Medium',
    'High',
    'Critical'
]

VALID_CATEGORIES = [
    'Infrastructure',
    'Electricity',
    'Water',
    'Internet',
    'Transport',
    'Service Issue',
    'Others'
]
ALLOWED_TRANSITIONS = {
    'Pending':     ['Assigned'],
    'Assigned':    ['In Progress'],
    'In Progress': ['Resolved', 'Escalated'],
    'Escalated':   ['In Progress'],
    'Resolved':    ['Closed'],
    'Closed':      []  # Final state — no transitions allowed
}


# ─── Document Builder ─────────────────────────────────────────────

def create_complaint_document(user_id, data, complaint_id):
    """
    Builds a complete complaint document ready for MongoDB insertion.
    user_id    → ObjectId of the logged-in user
    data       → request body from client
    complaint_id → generated human-readable ID like CMP-2024-0001
    """
    now = datetime.datetime.utcnow()

    return {
        "complaint_id": complaint_id,
        "user_id": user_id,
        "title": data['title'].strip(),
        "description": data['description'].strip(),
        "category": data['category'],
        "priority": data.get('priority', 'Medium'),
        "status": "Pending",          # Always starts as Pending
        "assigned_to": None,          # No admin assigned yet
        "attachments": [],            # Empty — added in Phase 9
        "status_history": [
            {
                "status": "Pending",
                "changed_by": user_id,
                "note": "Complaint submitted",
                "changed_at": now
            }
        ],
        "escalation_count": 0,
        "is_escalated": False,
        "resolved_at": None,
        "created_at": now,
        "updated_at": now
    }


def create_status_history_entry(status, changed_by, note=""):
    """
    Builds one status history entry.
    Called every time status changes.
    """
    return {
        "status": status,
        "changed_by": changed_by,
        "note": note,
        "changed_at": datetime.datetime.utcnow()
    }