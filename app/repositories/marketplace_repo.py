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
        Guards against duplicate/redundant requests.
        """
        # Check if a connection state already exists in EITHER direction
        existing_request = self.db.query(CollabRequest).filter(
            CollabRequest.tenant_id == tenant_id,
            (
                ((CollabRequest.sender_id == sender_id) & (CollabRequest.receiver_id == receiver_id)) |
                ((CollabRequest.sender_id == receiver_id) & (CollabRequest.receiver_id == sender_id))
            )
        ).first()

        # If a request exists, inspect its status to throw a highly descriptive error
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
            # Note: If it's DECLINED, we let them send a new one to try again!

        #If clean, proceed to persist the database record
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
        #Find the request in PostgreSQL
        request = self.db.query(CollabRequest).filter(CollabRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaboration request not found."
            )
            
        #Security Check: Ensure the person trying to accept/decline is actually the receiver
        if request.receiver_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this request."
            )
            
        #Update the status using your existing Enum type mappings safely
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
        #Find all accepted rows across this tenant ecosystem matching the current user id
        accepted_handshakes = self.db.query(CollabRequest).filter(
            CollabRequest.tenant_id == tenant_id,
            CollabRequest.status == CollabStatus.ACCEPTED,
            ((CollabRequest.sender_id == current_user_id) | (CollabRequest.receiver_id == current_user_id))
        ).all()

        if not accepted_handshakes:
            return []

        #Loop and pluck out the identity of the user on the OTHER end of the relationship
        partner_ids = []
        for req in accepted_handshakes:
            if req.sender_id == current_user_id:
                partner_ids.append(req.receiver_id)
            else:
                partner_ids.append(req.sender_id)

        #Resolve user profiles matching those collected primary keys
        return self.db.query(User).filter(User.id.in_(partner_ids)).all()