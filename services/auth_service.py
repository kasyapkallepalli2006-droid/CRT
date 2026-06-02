import bcrypt
import jwt
import datetime
from database.connections import db
from models.user_model import create_user_document, validate_user_input
from config import Config

def hash_password(plain_password):

    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)

    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password):

    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def generate_token(user_id, role):
    payload = {
        "user_id": str(user_id),
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(
        payload,
        Config.SECRET_KEY,
        algorithm="HS256"
    )

    return token


def decode_token(token):
    payload = jwt.decode(
        token,
        Config.SECRET_KEY,
        algorithms=["HS256"]
    )
    return payload

def register_user(data):
    is_valid, error = validate_user_input(
        data,
        ['name', 'email', 'password']
    )
    if not is_valid:
        return False, {"error": error}, 400

    if '@' not in data['email'] or '.' not in data['email']:
        return False, {"error": "Invalid email format"}, 400

    if len(data['password']) < 6:
        return False, {"error": "Password must be at least 6 characters"}, 400

    existing_user = db.users.find_one(
        {"email": data['email'].lower().strip()}
    )
    if existing_user:
        return False, {"error": "Email already registered"}, 409

    hashed = hash_password(data['password'])

    user_doc = create_user_document(
        name=data['name'],
        email=data['email'],
        hashed_password=hashed,
        role=data.get('role', 'user'),
        phone=data.get('phone')
    )

    result = db.users.insert_one(user_doc)

    return True, {
        "message": "Registration successful",
        "user_id": str(result.inserted_id)
    }, 201

def login_user(data):

    is_valid, error = validate_user_input(data, ['email', 'password'])
    if not is_valid:
        return False, {"error": error}, 400

    user = db.users.find_one(
        {"email": data['email'].lower().strip()}
    )

    if not user:
        return False, {"error": "Invalid email or password"}, 401

    if not user.get('is_active', True):
        return False, {"error": "Account is disabled"}, 403

    if not verify_password(data['password'], user['password']):
        return False, {"error": "Invalid email or password"}, 401

    token = generate_token(user['_id'], user['role'])

    return True, {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "role": user['role']
        }
    }, 200