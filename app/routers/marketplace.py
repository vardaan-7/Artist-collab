from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.models.collab import CollabRequest
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


#COMPOSITE GEOSPATIAL PROXIMITY SEARCH ENGINE
@router.get("/discover")
def discover_artists_by_proximity(
    role_type: str = Query(..., description="The type of artist you are searching for (e.g., producer)"),
    limit: int = Query(10, ge=1, le=50, description="Number of results per page"),
    cursor: Optional[str] = Query(None, description="The Base64 encoded composite cursor for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Returns a Google-style paginated list of target creators 
    sorted dynamically by physical proximity to the requesting artist.
    """
    # 🛡️ Safety Guard: Ensure the requesting user has spatial coordinates configured
    if current_user.latitude is None or current_user.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Your profile is missing location data. Please configure your latitude and longitude to use proximity search."
        )

    marketplace_repo = MarketplaceRepository(db)
    
    #spatial repository math engine
    paginated_results = marketplace_repo.get_artists_paginated_by_proximity(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        role_type=role_type,
        my_lat=current_user.latitude,
        my_lng=current_user.longitude,
        limit=limit,
        cursor=cursor
    )
    
    return paginated_results


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

@router.get("/requests/incoming")
def get_incoming_requests(
       current_user: User = Depends(get_current_user),
       db: Session = Depends(get_db)
   ):
       requests = db.query(CollabRequest).filter(
           CollabRequest.receiver_id == current_user.id,
           CollabRequest.status == "pending"
       ).all()
       
       return requests

@router.patch("/requests/{request_id}/status", response_model=CollabRequestResponse)
def respond_to_collab_request(
    request_id: int,
    action: str, # Expecting either "accepted" or "declined"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Allows the receiving artist to accept or decline an incoming request.
    """
    if action not in ["accepted", "declined"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'accepted' or 'declined'."
        )
        
    marketplace_repo = MarketplaceRepository(db)
    
    # Execute the update pipeline inside our repository
    updated_request = marketplace_repo.update_collab_request_status(
        request_id=request_id,
        current_user_id=current_user.id,
        new_status=action
    )
    
    return updated_request

@router.get("/connections", response_model=List[UserResponse])
def view_active_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Fetches profiles of all artists with whom the 
    authenticated user has established an accepted connection handshake.
    """
    marketplace_repo = MarketplaceRepository(db)
    connections = marketplace_repo.get_active_connections(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    return connections