from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import Config

def get_database():

    try:
        client = MongoClient(Config.MONGO_URI)
        client.admin.command('ping')

        db = client[Config.DATABASE_NAME]

        print("✅ MongoDB connected successfully!")
        return db

    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None

db = get_database()