from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.models.collab import CollabRequest, ChatMessage, CollabStatus

router = APIRouter(prefix="/chat", tags=["Chat"])

# --- PYDANTIC SCHEMAS ---
class MessageCreate(BaseModel):
    receiver_id: int
    message_text: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    message_text: str
    sent_at: datetime

    class Config:
        from_attributes = True

class ChatContactResponse(BaseModel):
    artist_id: int
    artist_name: str
    role_type: str

# --- AUTOMATED MVP RETENTION POLICY ---
def purge_expired_messages(db: Session):
    """
    Performance Guard: Flushes text logs older than 3 days automatically
    to keep PostgreSQL fast and lightweight.
    """
    try:
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        deleted_count = db.query(ChatMessage).filter(ChatMessage.sent_at < three_days_ago).delete()
        if deleted_count > 0:
            db.commit()
            print(f"[RETENTION] Purged {deleted_count} expired chat messages.")
    except Exception as e:
        db.rollback()
        print(f"[RETENTION ERROR] Failed to run automated cleanup: {str(e)}")

# --- ENDPOINTS ---

@router.post("/send", status_code=status.HTTP_201_CREATED)
def send_message(
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Sends a text message if an ACCEPTED handshake exists.
    """
    # Guardrail Check using your native Enum setup
    is_collab_valid = db.query(CollabRequest).filter(
        (
            ((CollabRequest.sender_id == current_user.id) & (CollabRequest.receiver_id == payload.receiver_id)) |
            ((CollabRequest.sender_id == payload.receiver_id) & (CollabRequest.receiver_id == current_user.id))
        ),
        CollabRequest.status == CollabStatus.ACCEPTED  # 🟢 Uses the native enum!
    ).first()

    if not is_collab_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat locked. You can only message an artist after a collaboration request is accepted."
        )

    new_msg = ChatMessage(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        message_text=payload.message_text
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    return {"status": "success", "message_id": new_msg.id}


@router.get("/history/{artist_id}", response_model=List[MessageResponse])
def get_chat_history(
    artist_id: int,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Fetches text log and runs the 3-day cleanup routine.
    """
    purge_expired_messages(db)

    messages = db.query(ChatMessage).filter(
        (
            ((ChatMessage.sender_id == current_user.id) & (ChatMessage.receiver_id == artist_id)) |
            ((ChatMessage.sender_id == artist_id) & (ChatMessage.receiver_id == current_user.id))
        )
    ).order_by(ChatMessage.sent_at.asc()).limit(limit).all()

    return messages


@router.get("/contacts", response_model=List[ChatContactResponse])
def get_active_chat_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected Endpoint: Lists your active accepted collaboration partners uniquely.
    """
    # 1. Fetch ALL connections involving the user that are accepted
    accepted_collabs = db.query(CollabRequest).filter(
        ((CollabRequest.sender_id == current_user.id) | (CollabRequest.receiver_id == current_user.id)),
        CollabRequest.status == CollabStatus.ACCEPTED
    ).all()

    # 2. Extract the other artist's ID from each handshake connection record
    partner_ids = set()
    for collab in accepted_collabs:
        target_id = collab.receiver_id if collab.sender_id == current_user.id else collab.sender_id
        if target_id != current_user.id:  # Double check to ensure we aren't adding yourself
            partner_ids.add(target_id)

    # 3. If no active handshakes exist, return early to save database operations
    if not partner_ids:
        return []

    # 4. Use SQL IN operator to grab all distinct user details in ONE clean query
    matching_artists = db.query(User).filter(User.id.in_(list(partner_ids))).all()

    # 5. Map the objects into the API schema output array format
    contacts = []
    for artist in matching_artists:
        contacts.append({
            "artist_id": artist.id,
            "artist_name": artist.artist_name,
            "role_type": getattr(artist, "role_type", "creator")
        })

    return contacts