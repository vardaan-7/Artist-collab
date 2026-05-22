from typing import List, Optional
from sqlalchemy.orm import Session
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