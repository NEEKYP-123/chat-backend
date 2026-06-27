from fastapi import APIRouter, Header, HTTPException
from database import users_col
from services.auth_service import decode_token
from pydantic import BaseModel
from bson import ObjectId

router = APIRouter(prefix="/users", tags=["users"])

class PublicKeyRequest(BaseModel):
    public_key: str

def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.get("/search")
async def search_users(q: str = "", authorization: str = Header(...)):
    """Search all app users by username or phone. Excludes the caller."""
    caller_id = get_user_id(authorization)
    if not q.strip():
        return []
    cursor = users_col.find({
        "_id": {"$ne": ObjectId(caller_id)},
        "$or": [
            {"username": {"$regex": q.strip(), "$options": "i"}},
            {"phone": {"$regex": q.strip(), "$options": "i"}},
        ],
    }, {"password": 0, "public_key": 0}).limit(20)
    results = []
    async for u in cursor:
        results.append({
            "id": str(u["_id"]),
            "username": u.get("username", ""),
            "avatar_url": u.get("avatar_url"),
            "phone": u.get("phone"),
        })
    return results


@router.patch("/me/public_key")
async def upload_public_key(body: PublicKeyRequest, authorization: str = Header(...)):
    user_id = get_user_id(authorization)
    await users_col.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"public_key": body.public_key}},
    )
    return {"status": "ok"}

@router.get("/{user_id}/public_key")
async def get_user_public_key(user_id: str, authorization: str = Header(...)):
    get_user_id(authorization)
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("public_key"):
        raise HTTPException(status_code=404, detail="Public key not found")
    return {"public_key": user["public_key"]}
