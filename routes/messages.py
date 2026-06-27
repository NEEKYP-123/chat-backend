from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from database import messages_col, users_col, rooms_col
from services.auth_service import decode_token
from websocket.manager import manager
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/rooms", tags=["messages"])

class ReactRequest(BaseModel):
    emoji: str

def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

def _fmt(m: dict, reply_msg: dict | None = None) -> dict:
    return {
        "id": str(m["_id"]),
        "room_id": m["room_id"],
        "sender_id": m["sender_id"],
        "sender_name": m["sender_name"],
        "content": m["content"],
        "type": m.get("type", "text"),
        "file_url": m.get("file_url"),
        "timestamp": m["timestamp"].isoformat(),
        "reactions": m.get("reactions", []),
        "reply_to_id": m.get("reply_to_id"),
        "reply_to_content": reply_msg["content"] if reply_msg else None,
        "reply_to_sender_name": reply_msg["sender_name"] if reply_msg else None,
        "is_encrypted": m.get("is_encrypted", False),
    }

@router.get("/{room_id}/messages")
async def get_messages(room_id: str, authorization: str = Header(...)):
    get_user_id(authorization)
    msgs = []
    async for m in messages_col.find({"room_id": room_id}).sort("timestamp", 1).limit(50):
        msgs.append(m)

    # Batch-resolve reply_to messages
    reply_ids = list({
        ObjectId(m["reply_to_id"]) for m in msgs
        if m.get("reply_to_id")
    })
    reply_lookup: dict[str, dict] = {}
    if reply_ids:
        async for rm in messages_col.find({"_id": {"$in": reply_ids}}):
            reply_lookup[str(rm["_id"])] = rm

    return [_fmt(m, reply_lookup.get(m.get("reply_to_id", ""))) for m in msgs]

@router.post("/{room_id}/messages/{message_id}/react")
async def react_to_message(
    room_id: str,
    message_id: str,
    body: ReactRequest,
    authorization: str = Header(...),
):
    user_id = get_user_id(authorization)
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    msg = await messages_col.find_one({"_id": ObjectId(message_id), "room_id": room_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    reactions = msg.get("reactions", [])

    # Toggle: if user already reacted with same emoji, remove it
    existing = next((r for r in reactions if r["user_id"] == user_id and r["emoji"] == body.emoji), None)
    if existing:
        reactions = [r for r in reactions if not (r["user_id"] == user_id and r["emoji"] == body.emoji)]
    else:
        # Remove any previous reaction from this user (one reaction per user)
        reactions = [r for r in reactions if r["user_id"] != user_id]
        reactions.append({
            "emoji": body.emoji,
            "user_id": user_id,
            "username": user["username"],
        })

    await messages_col.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"reactions": reactions}},
    )

    # Broadcast reaction update to all users in the room via WebSocket
    await manager.broadcast(room_id, {
        "type": "reaction_update",
        "message_id": message_id,
        "reactions": reactions,
    })

    return {"message_id": message_id, "reactions": reactions}
