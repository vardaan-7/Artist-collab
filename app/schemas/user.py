from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Base Shared User Schemas (Attributes shared across requests and responses)
class UserBase(BaseModel):
    email: EmailStr
    artist_name: str = Field(..., min_length=2, max_length=100)
    role_type: str = Field(..., description="Producer, Vocalist, Mixing Engineer, etc.")
    tenant_id: str
    
    # 🟢 NEW SHARED PROFILE ATTRIBUTES
    bio: Optional[str] = Field(
        "Hey there! Ready to jump onto some massive collaborative project tracks.", 
        description="Artist profile biography statement description"
    )
    latitude: Optional[float] = Field(None, description="Geographic latitude coordinate position")
    longitude: Optional[float] = Field(None, description="Geographic longitude coordinate position")

# Schema accepted when an artist registers (Needs the raw text password string)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plaintext raw password string")

# Schema used to return data safely back to the client browser UI (Hides the password!)
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    # Tells Pydantic to read raw SQLAlchemy database objects natively 
    class Config:
        from_attributes = True