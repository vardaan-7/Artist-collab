from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

#Initialize the central SQL Database Engine management pool
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI, 
    pool_pre_ping=True  # Automatically fixes disconnected/dropped background sessions safely
)

#Establish a SessionLocal execution factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Form the declarative base mapping entity
Base = declarative_base()

#Dependency Injection function to manage the Database Session lifecycle
def get_db():
    db = SessionLocal()
    try:
        yield db  
    finally:
        db.close()  