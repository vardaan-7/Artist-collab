import os
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.concurrency import run_in_threadpool
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.routers.deps import get_current_user
from app.models.user import User
from app.models.collab import CollabRequest
from app.repositories.marketplace_repo import MarketplaceRepository
from app.schemas.user import UserResponse
from app.schemas.collab import CollabRequestCreate, CollabRequestResponse

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
    marketplace_repo = MarketplaceRepository(db)
    return marketplace_repo.get_marketplace_artists(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        role_type=role_type
    )


@router.get("/discover")
def discover_artists_by_proximity(
    role_type: str = Query(..., description="The type of artist you are searching for (e.g., producer)"),
    limit: int = Query(10, ge=1, le=50, description="Number of results per page"),
    cursor: Optional[str] = Query(None, description="The Base64 encoded composite cursor for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.latitude is None or current_user.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Your profile is missing location data. Please configure your latitude and longitude to use proximity search."
        )

    marketplace_repo = MarketplaceRepository(db)
    return marketplace_repo.get_artists_paginated_by_proximity(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        my_lat=current_user.latitude,
        my_lng=current_user.longitude,
        role_type=role_type,
        limit=limit,
        cursor=cursor
    )


@router.post("/connect", response_model=CollabRequestResponse, status_code=status.HTTP_201_CREATED)
def initiate_collaboration(
    payload: CollabRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    marketplace_repo = MarketplaceRepository(db)
    if payload.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot initiate a collaboration request with yourself."
        )
        
    return marketplace_repo.create_collab_request(
        tenant_id=current_user.tenant_id,
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        message=payload.message
    )


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
    if action not in ["accepted", "declined"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'accepted' or 'declined'."
        )
        
    marketplace_repo = MarketplaceRepository(db)
    return marketplace_repo.update_collab_request_status(
        request_id=request_id,
        current_user_id=current_user.id,
        new_status=action
    )


@router.get("/connections", response_model=List[UserResponse])
def view_active_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    marketplace_repo = MarketplaceRepository(db)
    return marketplace_repo.get_active_connections(
        current_user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )


@router.post("/sync-audio-radar")
async def sync_audio_radar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    vector = await run_in_threadpool(extract_audio_features, audio_track.file_url)
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
                        "tenant_id": current_user.tenant_id,
                        "bio": getattr(current_user, "bio", "No profile bio available.") or "No profile bio available."
                    }
                )
            ]
        )
        return {
            "status": "synchronized",
            "message": f"Sonic vector footprint compiled successfully for '{current_user.artist_name}'!"
        }
    except Exception as e:
        traceback.print_exc()
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
    try:
        # 1. Retrieve origin user's vector
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
            
        raw_data = point_result[0].vector
        if isinstance(raw_data, dict):
            my_vector = [float(x) for x in list(raw_data.values())[0]]
        else:
            my_vector = [float(x) for x in raw_data]

        # 2. Query Qdrant with tenant isolation and self-exclusion filters
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=current_user.tenant_id)
                )
            ],
            must_not=[
                models.FieldCondition(
                    key="artist_id",
                    match=models.MatchValue(value=current_user.id)
                )
            ]
        )

        # Supports query_points with fallback to search
        if hasattr(qdrant_client, "query_points"):
            response = qdrant_client.query_points(
                collection_name="artist_audio_radar",
                query=my_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            search_results = response.points
        else:
            search_results = qdrant_client.search(
                collection_name="artist_audio_radar",
                query_vector=my_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )

        matches = []
        for match in search_results:
            payload_data = match.payload or {}
            raw_score = match.score
            # Normalize to 0-100% integer
            percentage = int(max(0.0, raw_score) * 100)

            matches.append({
                "id": payload_data.get("artist_id"),
                "artist_name": payload_data.get("artist_name"),
                "role_type": payload_data.get("role_type"),
                "bio": payload_data.get("bio", "No profile bio available."),
                "similarity_score": round(raw_score, 4),
                "score": round(raw_score, 4),
                "match_percentage": percentage,
                "match_percentage_str": f"{percentage}%"
            })

        return {
            "search_origin_artist": current_user.artist_name,
            "similar_creators": matches
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector matching index scan failed: {str(e)}"
        )