import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    """
    Checks if uploaded file has an allowed extension.

    How it works:
    "photo.jpg"  → split by "." → ["photo", "jpg"]
    → take last part → "jpg"
    → check if "jpg" is in ALLOWED_EXTENSIONS
    → True

    "malware.exe" → "exe" not in set → False
    """
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )

def generate_safe_filename(original_filename):
    """
    Creates a safe, unique filename for storage.

    Why we rename files:
    1. Original name might contain dangerous characters: "../etc/passwd.jpg"
    2. Two users might upload "photo.jpg" — they'd overwrite each other
    3. UUID makes every filename globally unique

    Example:
    "my photo!!.jpg" → secure → "my_photo__.jpg" → UUID prefix →
    "a3f8c2d1-4b5e-6f7a-8b9c-0d1e2f3a4b5c_my_photo__.jpg"
    """
    safe_name = secure_filename(original_filename)

    unique_id = str(uuid.uuid4())

    return f"{unique_id}_{safe_name}"

def save_file(file):
    """
    Saves an uploaded file to the uploads folder.
    Returns (success, filename or error_message)

    'file' here is a Flask FileStorage object from request.files
    """
    if not file or file.filename == '':
        return False, "No file selected"

    if not allowed_file(file.filename):
        return False, (
            f"File type not allowed. "
            f"Allowed types: {Config.ALLOWED_EXTENSIONS}"
        )

    filename = generate_safe_filename(file.filename)

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    return True, filename

def delete_file(filename):
    """
    Deletes a file from the uploads folder.
    Returns (success, message)
    """
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return False, "File not found on server"

    os.remove(filepath)
    return True, "File deleted successfully"

def get_file_extension(filename):
    """Returns the file extension. Example: 'photo.jpg' → 'jpg'"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''