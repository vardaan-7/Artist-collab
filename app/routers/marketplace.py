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
import requests

# Audio Radar Engine Modules
from app.services.audio_processor import extract_audio_features
from app.core.qdrant_setup import qdrant_client
from qdrant_client.http import models

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
    artists = marketplace_repo.get_marketplace_artists(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        role_type=role_type
    )
    return artists


# COMPOSITE GEOSPATIAL PROXIMITY SEARCH ENGINE
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
    if current_user.latitude is None or current_user.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Your profile is missing location data. Please configure your latitude and longitude to use proximity search."
        )

    marketplace_repo = MarketplaceRepository(db)
    paginated_results = marketplace_repo.get_artists_paginated_by_proximity(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        role_type=role_type,
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
    if payload.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot initiate a collaboration request with yourself."
        )
        
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
    action: str, 
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


# AUDIO SIMILARITY RADAR ENDPOINTS ───────────────────────────────────────

@router.post("/sync-audio-radar")
def sync_audio_radar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Extracts 33 numerical traits from the user's 
    signature track file and index maps it inside the Qdrant vector system.
    """
    if not getattr(current_user, "portfolios", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You haven't uploaded any items to your portfolio yet."
        )

    audio_track = next((item for item in current_user.portfolios if item.file_type == "audio"), None)
    if not audio_track or not audio_track.file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary audio track asset located inside your portfolio profile."
        )

    # Automatically parses the web link URL, downloads locally, and extracts vectors
    vector = extract_audio_features(audio_track.file_url)
    if not vector:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to compile numerical sonic characteristics from file."
        )

    try:
        qdrant_client.upsert(
            collection_name="artist_audio_radar",
            points=[
                models.PointStruct(
                    id=current_user.id,
                    vector=vector,
                    payload={
                        "artist_id": current_user.id,
                        "artist_name": current_user.artist_name,
                        "role_type": current_user.role_type,
                        "tenant_id": current_user.tenant_id
                    }
                )
            ]
        )
        return {
            "status": "synchronized",
            "message": f"Sonic vector footprint compiled successfully for '{current_user.artist_name}'!"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Qdrant storage cluster upload failure: {str(e)}"
        )


@router.get("/discover/audio")
def discover_by_audio_similarity(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Searches Qdrant for other artists whose music files 
    sound closest to the current user's profile track based on vector angles.
    """
    try:
        # 1. Fetch current user's vector map from Qdrant directly to use as query seed
        point_result = qdrant_client.retrieve(
            collection_name="artist_audio_radar",
            ids=[current_user.id],
            with_vectors=True
        )
        
        if not point_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Your sonic fingerprint vector hasn't been generated yet. Please sync your track first."
            )
            
        # Print out exactly what the structure looks like to your Uvicorn console for debugging
        raw_data = point_result[0].vector
        if isinstance(raw_data, dict):
            my_vector = [float(x) for x in list(raw_data.values())[0]]
        else:
            my_vector = [float(x) for x in raw_data]


        # 2 RAW HTTP REST FALLBACK: Bypasses client version limits completely
        # Adjust URL if your app reads host/port configuration from your setup variables
        qdrant_url = f"http://localhost:6333/collections/artist_audio_radar/points/search"
        
        payload = {
          "vector": my_vector,
          "filter": {
            "must": [
              {
                "key": "tenant_id",
                "match": {
                  "value": current_user.tenant_id
                }
              }
            ],
            "must_not": [
              {
                "key": "artist_id",
                "match": {
                  "value": current_user.id
                }
              }
            ]
          },
          "limit": limit,
          "with_payload": True
        }

        response = requests.post(qdrant_url, json=payload, timeout=5)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Qdrant engine REST endpoint rejected request: {response.text}"
            )
            
        search_results = response.json().get("result", [])

        # 3. Format matches into a clean tracking response payload map
        matches = []
        for match in search_results:
            matches.append({
                "artist_id": match.get("payload", {}).get("artist_id"),
                "artist_name": match.get("payload", {}).get("artist_name"),
                "role_type": match.get("payload", {}).get("role_type"),
                "match_score": round(match.get("score", 0) * 100, 2)
            })

        return {
            "search_origin_artist": current_user.artist_name,
            "similar_creators": matches
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector matching index scan failed: {str(e)}"
        )
        return {
            "search_origin_artist": current_user.artist_name,
            "similar_creators": matches
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector matching index scan failed: {str(e)}"
        )