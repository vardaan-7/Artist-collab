from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import SecurityManager
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.routers.deps import get_current_user 
from app.models.user import User
from app.models.media import MediaPortfolio 

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_artist(payload: UserCreate, db: Session = Depends(get_db)):
    """
    The endpoint that handles registering a brand new artist.
    """
    user_repo = UserRepository(db)
    
    existing_user = user_repo.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An artist account with this email already exists."
        )
    
    secure_hash = SecurityManager.hash_password(payload.password)
    new_user = user_repo.create_user(payload, secure_hash)
    return new_user


@router.post("/login")
def login_artist(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Authenticates an artist's credentials and issues a cryptographic JWT access token session.
    """
    user_repo = UserRepository(db)
    
    user = user_repo.get_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not SecurityManager.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = SecurityManager.create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_authenticated_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)  
):
    """
    Retrieves the private profile of the currently logged-in artist along with their signature song preview.
    """
    signature_track = db.query(MediaPortfolio).filter(MediaPortfolio.user_id == current_user.id).first()
    current_user.signature_track = signature_track
    return current_user


@router.patch("/update-location", status_code=status.HTTP_200_OK)
def update_location(
    payload: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the geospatial latitude and longitude coordinates of the authenticated artist.
    """
    try:
        current_user.latitude = payload.latitude
        current_user.longitude = payload.longitude
        
        db.commit()
        db.refresh(current_user)
        return {"status": "success", "message": "Location updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location metrics: {str(e)}"
        )