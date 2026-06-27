from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 10080))

ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")

STORJ_ACCESS_KEY = os.getenv("STORJ_ACCESS_KEY")
STORJ_SECRET_KEY = os.getenv("STORJ_SECRET_KEY")
STORJ_BUCKET = os.getenv("STORJ_BUCKET")
STORJ_ENDPOINT = os.getenv("STORJ_ENDPOINT")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
