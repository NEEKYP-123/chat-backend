from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
rooms_col = db["rooms"]
messages_col = db["messages"]
contacts_col = db["contacts"]
stories_col = db["stories"]
