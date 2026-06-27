from fastapi import APIRouter, HTTPException
from database import users_col
from models.user import RegisterRequest, LoginRequest, UserResponse
from services.auth_service import hash_password, verify_password, create_token
from bson import ObjectId

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(body: RegisterRequest):
    existing = await users_col.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = {
        "username": body.username,
        "email": body.email,
        "password": hash_password(body.password),
        "avatar_url": None,
        "onesignal_player_id": None,
    }
    result = await users_col.insert_one(user)
    token = create_token(str(result.inserted_id))
    return {"token": token, "user_id": str(result.inserted_id), "username": body.username}

@router.post("/login")
async def login(body: LoginRequest):
    user = await users_col.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(user["_id"]))
    return {"token": token, "user_id": str(user["_id"]), "username": user["username"]}
