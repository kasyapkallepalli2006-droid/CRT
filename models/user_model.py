import datetime

ROLES = ['user', 'admin']

def create_user_document(name, email, hashed_password, role='user', phone=None):

    return {
        "name": name.strip(),
        "email": email.lower().strip(),  # Always store email lowercase
        "password": hashed_password,
        "role": role,
        "phone": phone,
        "is_active": True,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    }

def validate_user_input(data, require_fields):
    for field in require_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
        if not str(data[field]).strip():
            return False, f"Field '{field}' cannot be empty"
    return True, None