import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Prioritize Render's live environment variable over local settings
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

# Ensure compatibility if the connection string uses the older postgres:// prefix
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Initialize the central SQL Database Engine management pool
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True  # Automatically fixes disconnected/dropped background sessions safely
)

# Establish a SessionLocal execution factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Form the declarative base mapping entity
Base = declarative_base()

# Dependency Injection function to manage the Database Session lifecycle
def get_db():
    db = SessionLocal()
    try:
        yield db  
    finally:
        db.close()