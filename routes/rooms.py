from fastapi import APIRouter, Header, HTTPException
from database import rooms_col
from models.room import CreateRoomRequest, RoomResponse
from services.auth_service import decode_token
from bson import ObjectId

router = APIRouter(prefix="/rooms", tags=["rooms"])

def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@router.get("/")
async def get_rooms(authorization: str = Header(...)):
    user_id = get_user_id(authorization)
    cursor = rooms_col.find({"members": user_id})
    rooms = []
    async for room in cursor:
        rooms.append({"id": str(room["_id"]), "name": room["name"],
                       "is_group": room["is_group"], "members": room["members"]})
    return rooms

@router.post("/")
async def create_room(body: CreateRoomRequest, authorization: str = Header(...)):
    user_id = get_user_id(authorization)
    members = list(set([user_id] + body.member_ids))

    # For 1:1 chats reuse an existing room between the same two members
    if not body.is_group and len(members) == 2:
        existing = await rooms_col.find_one({
            "is_group": False,
            "members": {"$all": members, "$size": 2},
        })
        if existing:
            return {"id": str(existing["_id"]), "name": existing["name"],
                    "is_group": existing["is_group"], "members": existing["members"]}

    room = {"name": body.name, "is_group": body.is_group, "members": members}
    result = await rooms_col.insert_one(room)
    return {"id": str(result.inserted_id), "name": body.name,
            "is_group": body.is_group, "members": members}
