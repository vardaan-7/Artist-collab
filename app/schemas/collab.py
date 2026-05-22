from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CollabRequestCreate(BaseModel):
    receiver_id: int
    message: Optional[str] = None

class CollabRequestResponse(BaseModel):
    id: int
    tenant_id: str
    sender_id: int
    receiver_id: int
    status: str
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True