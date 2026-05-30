from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class MediaPortfolio(Base):
    __tablename__ = "media_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    # Links the 10-second preview clip directly to the artist's profile
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Core File Metadata
    title = Column(String(100), nullable=False)          # e.g., "Dark Synth Loop 90BPM"
    file_type = Column(String(20), nullable=False)       # "audio" or "image"
    file_url = Column(String(500), nullable=False)       # Streaming link from your MinIO container
    mime_type = Column(String(50), nullable=False)       # e.g., "audio/mpeg" or "audio/wav"
    
    # AI Feature Enrichment
    # We use JSON so the AI model can store multiple dynamic niche tags 
    # e.g., ["lo-fi", "chill-hop", "ambient-pads"]
    niche_tags = Column(JSON, nullable=True, default=[]) 
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Bidirectional relationship back to the main User model
    artist = relationship("User", back_populates="portfolios")