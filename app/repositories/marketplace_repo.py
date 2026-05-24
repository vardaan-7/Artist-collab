import base64
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.user import User
from app.models.collab import CollabRequest, CollabStatus

class MarketplaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_marketplace_artists(
        self, 
        current_user_id: int, 
        tenant_id: str, 
        role_type: Optional[str] = None
    ) -> List[User]:
        """
        Fetches all artists in the same tenant, excluding the current user.
        Optionally filters by artist role type.
        """
        query = self.db.query(User).filter(
            User.tenant_id == tenant_id,
            User.id != current_user_id
        )
        
        if role_type:
            query = query.filter(User.role_type == role_type.lower())
            
        return query.all()

    # 🟢 INTEGRATED COMPOSITE GEOSPATIAL PROXIMITY ENGINE
    def get_artists_paginated_by_proximity(
        self,
        current_user_id: int,
        tenant_id: str,
        role_type: str,
        my_lat: float,
        my_lng: float,
        limit: int = 10,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates distance using the Haversine formula directly in SQL, 
        sorts by closest proximity first, and implements a state-stable composite cursor.
        """
        #Raw Haversine segment to calculate dynamic spatial radius distance matrix values in KM
        distance_formula = """
            (6371 * acos(
                GREATEST(-1.0, LEAST(1.0, 
                    cos(radians(:my_lat)) * cos(radians(latitude)) * cos(radians(longitude) - radians(:my_lng)) + 
                    sin(radians(:my_lat)) * sin(radians(latitude))
                ))
            ))
        """

        base_query = f"""
            SELECT id, artist_name, role_type, bio, tenant_id, latitude, longitude,
                   {distance_formula} AS distance
            FROM users
            WHERE tenant_id = :tenant_id 
              AND id != :current_user_id
              AND role_type = :role_type
              AND latitude IS NOT NULL 
              AND longitude IS NOT NULL
        """

        cursor_filter = ""
        query_params = {
            "my_lat": my_lat,
            "my_lng": my_lng,
            "tenant_id": tenant_id,
            "current_user_id": current_user_id,
            "role_type": role_type.lower(),
            "limit": limit
        }

        # 🔄 Handle decoding the multi-column composite boundary context state
        if cursor:
            try:
                decoded_bytes = base64.b64decode(cursor)
                cursor_data = json.loads(decoded_bytes)
                
                last_distance = float(cursor_data["distance"])
                last_id = int(cursor_data["id"])
                
                # Rule boundary logic: Further out in distance, or exact same distance with higher ID increment
                cursor_filter = """
                    AND (
                        {distance_formula} > :last_distance 
                        OR ({distance_formula} = :last_distance AND id > :last_id)
                    )
                """.format(distance_formula=distance_formula)
                
                query_params["last_distance"] = last_distance
                query_params["last_id"] = last_id
            except Exception:
                pass # Fail-safe fallback: Reset to first results page if cursor is malformed

        full_sql = f"""
            {base_query}
            {cursor_filter}
            ORDER BY distance ASC, id ASC
            LIMIT :limit
        """

        result = self.db.execute(text(full_sql), query_params).all()

        artists_list = []
        for row in result:
            artists_list.append({
                "id": row.id,
                "artist_name": row.artist_name,
                "role_type": row.role_type,
                "bio": row.bio,
                "distance_km": round(row.distance, 2)
            })

        next_cursor = None
        has_more = len(artists_list) == limit

        # 🔐 Construct clean, obfuscated token pointers for subsequent pages
        if has_more and artists_list:
            last_item = artists_list[-1]
            cursor_payload = {
                "distance": last_item["distance_km"],
                "id": last_item["id"]
            }
            serialized_payload = json.dumps(cursor_payload)
            next_cursor = base64.b64encode(serialized_payload.encode()).decode()

        return {
            "artists": artists_list,
            "paging": {
                "next_cursor": next_cursor,
                "has_more": has_more
            }
        }

    def create_collab_request(
        self, 
        tenant_id: str, 
        sender_id: int, 
        receiver_id: int, 
        message: Optional[str] = None
    ) -> CollabRequest:
        """
        Persists a brand new collaboration handshake request between two artists.
        Guards against duplicate/redundant requests.
        """
        existing_request = self.db.query(CollabRequest).filter(
            CollabRequest.tenant_id == tenant_id,
            (
                ((CollabRequest.sender_id == sender_id) & (CollabRequest.receiver_id == receiver_id)) |
                ((CollabRequest.sender_id == receiver_id) & (CollabRequest.receiver_id == sender_id))
            )
        ).first()

        if existing_request:
            if existing_request.status == CollabStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A pending collaboration handshake invitation already exists between you two."
                )
            elif existing_request.status == CollabStatus.ACCEPTED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You are already active collaboration partners with this artist!"
                )

        db_request = CollabRequest(
            tenant_id=tenant_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message,
            status=CollabStatus.PENDING
        )
        self.db.add(db_request)
        self.db.commit()
        self.db.refresh(db_request)
        return db_request
    
    def update_collab_request_status(self, request_id: int, current_user_id: int, new_status: str) -> CollabRequest:
        """
        Looks up a pending collaboration request, ensures the current user is 
        actually the authorized receiver, and updates the status.
        """
        request = self.db.query(CollabRequest).filter(CollabRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaboration request not found."
            )
            
        if request.receiver_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this request."
            )
            
        try:
            request.status = CollabStatus(new_status.upper()).value
        except ValueError:
            try:
                request.status = CollabStatus(new_status.lower()).value
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status conversion value: {new_status}"
                )

        self.db.commit()
        self.db.refresh(request)
        return request

    def get_active_connections(self, current_user_id: int, tenant_id: str) -> List[User]:
        """
        Fetches full User profiles for anyone who has an 'ACCEPTED' 
        collaboration state with the current user.
        """
        accepted_handshakes = self.db.query(CollabRequest).filter(
            CollabRequest.tenant_id == tenant_id,
            CollabRequest.status == CollabStatus.ACCEPTED,
            ((CollabRequest.sender_id == current_user_id) | (CollabRequest.receiver_id == current_user_id))
        ).all()

        if not accepted_handshakes:
            return []

        partner_ids = []
        for req in accepted_handshakes:
            if req.sender_id == current_user_id:
                partner_ids.append(req.receiver_id)
            else:
                partner_ids.append(req.sender_id)

        return self.db.query(User).filter(User.id.in_(partner_ids)).all()