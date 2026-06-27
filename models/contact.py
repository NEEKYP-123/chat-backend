from pydantic import BaseModel
from typing import Optional

class AddContactRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
