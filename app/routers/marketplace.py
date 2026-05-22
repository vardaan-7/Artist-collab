from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.repositories.marketplace_repo import MarketplaceRepository
from app.schemas.user import UserResponse
from app.schemas.collab import CollabRequestCreate, CollabRequestResponse

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.get("/artists", response_model=List[UserResponse])
def browse_marketplace(
    role_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Allows an authenticated artist to view all other available 
    creators matching their platform tenant workspace, filtered optionally by role.
    """
    marketplace_repo = MarketplaceRepository(db)
    
    # Fetch artists while automatically ignoring the user making the request
    artists = marketplace_repo.get_marketplace_artists(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        role_type=role_type
    )
    return artists


@router.post("/connect", response_model=CollabRequestResponse, status_code=status.HTTP_201_CREATED)
def initiate_collaboration(
    payload: CollabRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Dispatches a collaboration handshake invitation 
    to another creator within the same tenant layer.
    """
    marketplace_repo = MarketplaceRepository(db)
    
    #To ensure you aren't trying to collaborate with yourself
    if payload.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot initiate a collaboration request with yourself."
        )
        
    #database record creation
    new_request = marketplace_repo.create_collab_request(
        tenant_id=current_user.tenant_id,
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        message=payload.message
    )
    return new_request