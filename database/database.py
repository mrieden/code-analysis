import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME     = os.getenv("DB_NAME", "owlint")

client = AsyncIOMotorClient(MONGODB_URL)
db     = client[DB_NAME]

# Collections:
# db.users    — GitHub user profiles
# db.history  — Code analysis history per user
