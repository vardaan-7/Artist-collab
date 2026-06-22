from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.storage import storage_service
from app.models.media import MediaPortfolio
from app.models.user import User           # 💡 Added import for your User model
import app.schemas.media as schema_media
from app.schemas.user import UserResponse  # 💡 Added import for the upgraded UserResponse schema

router = APIRouter(prefix="/media", tags=["Media Portfolio Operations"])

@router.post("/upload-snippet", response_model=schema_media.MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_snippet(
    title: str = Form(...),                    # Sent as form data alongside the file
    user_id: int = Form(...),                  # The ID of the artist uploading the file
    file: UploadFile = File(...),              # The raw multi-part binary stream data
    db: Session = Depends(get_db)
):
    """
    Accepts a 10-second audio track preview, streams it over to our MinIO container,
    and returns the fully registered database metadata trace record.
    """
    # 1. Catch un-supported non-audio assets early to keep your storage healthy
    if not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid asset footprint profile: This endpoint accepts audio formats only."
        )

    # 2. Stream the raw data to your local MinIO object storage container
    try:
        saved_file_url = await storage_service.upload_audio_snippet(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage engine pipeline failure: {str(e)}"
        )

    # 3. Create the Database Record
    new_media = MediaPortfolio(
        user_id=user_id,
        title=title,
        file_type="audio",
        file_url=saved_file_url,
        mime_type=file.content_type,
        niche_tags=[]  # 🔮 Future AI Model Target: e.g., ["synthwave", "lo-fi"]
    )

    db.add(new_media)
    db.commit()
    db.refresh(new_media)

    return new_media


# 🟢 NEW PROFILE LOOKUP ENDPOINT
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
    # Pydantic matches this with our 'signature_track: Optional[MediaResponse] = None' field
    artist.signature_track = signature_track
    
    return artist