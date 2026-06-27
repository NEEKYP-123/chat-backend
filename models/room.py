from pydantic import BaseModel
from typing import List

class CreateRoomRequest(BaseModel):
    name: str
    member_ids: List[str]  # list of user IDs to add
    is_group: bool = False

class RoomResponse(BaseModel):
    id: str
    name: str
    is_group: bool
    members: List[str]
