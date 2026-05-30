from sqlalchemy import Column, Integer, String, Boolean, DateTime,Float,Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    # Enforce the explicit database physical table name signature
    __tablename__ = "users"

    # Core relational identification keys
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Business Logic parameters
    artist_name = Column(String(100), nullable=False)
    role_type = Column(String(50), nullable=False)  # e.g., "Producer", "Vocalist", "Guitarist"
    tenant_id = Column(String(50), index=True, nullable=False) # Multi-tenant security isolation tag
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit trail time signatures (Tracks exactly when an account was created)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    #bio
    bio = Column(Text, nullable=True)
    
    # GEOSPATIAL DATA TRACKING FIELDS
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    portfolios = relationship("MediaPortfolio", back_populates="artist", cascade="all, delete-orphan")
    