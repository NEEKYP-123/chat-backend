from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageResponse(BaseModel):
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    type: str               # "text" | "image" | "file"
    file_url: Optional[str] = None
    timestamp: datetime
