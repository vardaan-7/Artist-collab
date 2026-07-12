from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.storage import storage_service
from app.models.media import MediaPortfolio
from app.models.user import User 
from app.routers.deps import get_current_user
import app.schemas.media as schema_media
from app.schemas.user import UserResponse 

router = APIRouter(prefix="/media", tags=["Media Portfolio Operations"])

@router.post("/upload-snippet", response_model=schema_media.MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_snippet(
    title: str = Form(...), 
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts an audio track preview, ensures only a single signature track exists,
    streams it over to storage, and returns the registered database metadata trace record.
    """
    # 1. Structural Validation Gate: Block upload if a track already exists for this user
    existing_track = db.query(MediaPortfolio).filter(MediaPortfolio.user_id == current_user.id).first()
    if existing_track:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active signature preview track. Delete it before uploading a new one."
        )

    # 2. Catch un-supported non-audio assets early to keep your storage healthy
    if not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid asset footprint profile: This endpoint accepts audio formats only."
        )

    # 3. Stream the raw data to the storage container
    try:
        saved_file_url = await storage_service.upload_audio_snippet(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage engine pipeline failure: {str(e)}"
        )

    # 4. Create the Database Record using the authenticated user ID and tenant ID
    new_media = MediaPortfolio(
        user_id=current_user.id,
        title=title,
        file_type="audio",
        file_url=saved_file_url,
        mime_type=file.content_type,
        tenant_id=current_user.tenant_id,
        niche_tags=[] 
    )

    db.add(new_media)
    db.commit()
    db.refresh(new_media)

    return new_media


@router.get("/artist/{artist_name}", response_model=UserResponse)
def get_artist_profile_by_name(artist_name: str, db: Session = Depends(get_db)):
    """
    Looks up an artist by their name, fetches their single signature track record,
    and returns a nested profile payload for the frontend UI profile page.
    """
    # 1. Look up the artist profile using the unique artist_name field from the User table
    artist = db.query(User).filter(User.artist_name == artist_name).first()
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artist '{artist_name}' could not be found."
        )
    
    # 2. Query your MediaPortfolio table to pull their single signature asset
    signature_track = db.query(MediaPortfolio).filter(MediaPortfolio.user_id == artist.id).first()
    
    # 3. Dynamically inject the file object into our SQLAlchemy user instance
    artist.signature_track = signature_track
    
    return artist