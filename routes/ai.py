from fastapi import APIRouter, Header, HTTPException
from database import messages_col, users_col
from services.auth_service import decode_token
from services.groq_service import get_reply_suggestions
from pydantic import BaseModel
from bson import ObjectId

router = APIRouter(prefix="/ai", tags=["ai"])

class SuggestRequest(BaseModel):
    room_id: str

def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.post("/suggest")
async def suggest_replies(body: SuggestRequest, authorization: str = Header(...)):
    user_id = get_user_id(authorization)

    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch last 10 text messages from the room
    cursor = messages_col.find(
        {"room_id": body.room_id, "type": "text"}
    ).sort("timestamp", -1).limit(10)

    msgs = []
    async for m in cursor:
        msgs.append({
            "sender_name": m["sender_name"],
            "content": m["content"],
            "type": m.get("type", "text"),
        })
    msgs.reverse()  # oldest first for context

    if not msgs:
        raise HTTPException(status_code=400, detail="No messages to base suggestions on")

    try:
        suggestions = await get_reply_suggestions(msgs, user["username"])
        return {"suggestions": suggestions}
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            raise HTTPException(status_code=429, detail="AI quota exceeded. Try again later.")
        raise HTTPException(status_code=500, detail=f"AI error: {err}")
