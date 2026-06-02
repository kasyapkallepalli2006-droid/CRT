import re

def validate_email(email):
    """
    Validates email format using regex.
    Returns (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        return False, "Email is required"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, None


def validate_password(password):
    """
    Validates password strength.
    Returns (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 50:
        return False, "Password must be less than 50 characters"
    return True, None


def validate_required_fields(data, fields):
    """
    Checks all required fields exist and are non-empty.
    Returns (is_valid, error_message)
    """
    if not data:
        return False, "Request body is empty"
    for field in fields:
        if field not in data:
            return False, f"Missing required field: '{field}'"
        if isinstance(data[field], str) and not data[field].strip():
            return False, f"Field '{field}' cannot be empty"
    return True, None


def validate_string_length(value, field_name, min_len=1, max_len=500):
    """
    Validates string length boundaries.
    Returns (is_valid, error_message)
    """
    if not value or not isinstance(value, str):
        return False, f"'{field_name}' must be a non-empty string"
    length = len(value.strip())
    if length < min_len:
        return False, f"'{field_name}' must be at least {min_len} characters"
    if length > max_len:
        return False, f"'{field_name}' must be less than {max_len} characters"
    return True, None