from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from database import stories_col, contacts_col, users_col
from services.auth_service import decode_token
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta

router = APIRouter(prefix="/stories", tags=["stories"])

class StoryRequest(BaseModel):
    media_url: str
    type: str = "image"  # image | video

def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

def _fmt(s: dict) -> dict:
    return {
        "id": str(s["_id"]),
        "user_id": s["user_id"],
        "username": s["username"],
        "media_url": s["media_url"],
        "type": s.get("type", "image"),
        "created_at": s["created_at"].isoformat(),
        "expires_at": s["expires_at"].isoformat(),
    }

@router.post("/")
async def post_story(body: StoryRequest, authorization: str = Header(...)):
    user_id = get_user_id(authorization)
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.utcnow()
    story = {
        "user_id": user_id,
        "username": user["username"],
        "media_url": body.media_url,
        "type": body.type,
        "created_at": now,
        "expires_at": now + timedelta(hours=24),
    }
    result = await stories_col.insert_one(story)
    story["_id"] = result.inserted_id
    return _fmt(story)

@router.get("/")
async def get_stories(authorization: str = Header(...)):
    """Get active stories from self + contacts."""
    user_id = get_user_id(authorization)
    now = datetime.utcnow()

    # Get contact user IDs
    contact_user_ids = []
    async for c in contacts_col.find({"owner_id": user_id, "user_id": {"$ne": None}}):
        contact_user_ids.append(c["user_id"])

    # Include own stories
    allowed_ids = [user_id] + contact_user_ids

    # Group by user_id, latest story per user
    pipeline = [
        {"$match": {"user_id": {"$in": allowed_ids}, "expires_at": {"$gt": now}}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$user_id",
            "doc": {"$first": "$$ROOT"},
            "count": {"$sum": 1},
        }},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$doc", {"story_count": "$count"}]}}},
        {"$sort": {"created_at": -1}},
    ]

    result = []
    async for s in stories_col.aggregate(pipeline):
        d = _fmt(s)
        d["story_count"] = s.get("story_count", 1)
        result.append(d)

    return result
