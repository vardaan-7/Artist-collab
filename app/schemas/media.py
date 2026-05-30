from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

#Base Shared Attributes (What every media schema needs)
class MediaBase(BaseModel):
    title: str
    file_type: str  # "audio" or "image"

#Schema for creating a new entry (Used internally after upload)
class MediaCreate(MediaBase):
    user_id: int
    file_url: str
    mime_type: str
    niche_tags: Optional[List[str]] = []

#Schema for returning media details back to the client/frontend
class MediaResponse(MediaBase):
    id: int
    user_id: int
    file_url: str
    mime_type: str
    niche_tags: List[str]
    created_at: datetime

    # Tell Pydantic to read standard ORM models (SQLAlchemy objects) smoothly
    model_config = {"from_attributes": True}