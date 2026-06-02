import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'complaint_platform_db')
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')

    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  