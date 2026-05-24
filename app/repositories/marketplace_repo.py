from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from fastapi import HTTPException, status
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
            query = query.filter(User.role_type == role_type)
            
        return query.all()

    def create_collab_request(
        self, 
        tenant_id: str, 
        sender_id: int, 
        receiver_id: int, 
        message: Optional[str] = None
    ) -> CollabRequest:
        """
        Persists a brand new collaboration handshake request between two artists.
        """
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
        # 1. Find the request in PostgreSQL
        request = self.db.query(CollabRequest).filter(CollabRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaboration request not found."
            )
            
        # 2. Security Check: Ensure the person trying to accept/decline is actually the receiver
        if request.receiver_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this request."
            )
            
        # 3. Update the status using your existing Enum type mappings safely
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