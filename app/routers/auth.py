from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import SecurityManager
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.routers.deps import get_current_user 
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


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


#The Protected Route: Only accessible if a valid JWT token is provided!
@router.get("/me", response_model=UserResponse)
def get_authenticated_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieves the private profile of the currently logged-in artist.
    """
    return current_user