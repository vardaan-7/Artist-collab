from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import SecurityManager
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserResponse

#Create the router (like a controller prefix in Spring Boot)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_artist(payload: UserCreate, db: Session = Depends(get_db)):
    """
    The endpoint that handles registering a brand new artist.
    """
    #Connect to our data layer
    user_repo = UserRepository(db)
    
    #Business Check: Does this email already exist?
    existing_user = user_repo.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An artist account with this email already exists."
        )
    
    #Security Layer: Hash the plaintext password
    secure_hash = SecurityManager.hash_password(payload.password)
    
    #Persistence Layer: Save the user record to PostgreSQL
    new_user = user_repo.create_user(payload, secure_hash)
    
    #Return the clean profile back to the browser (automatically filters out password)
    return new_user