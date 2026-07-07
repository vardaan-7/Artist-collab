import os
import tempfile
import requests
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.media import MediaPortfolio
from app.services.audio_processor import extract_audio_features
from app.core.qdrant_setup import qdrant_client
from qdrant_client.http import models

def download_temporary_audio(url: str) -> str:
    """Downloads a file from a URL to a temporary local file path."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Create a temporary file that won't lock on Windows
        suffix = ".mp3" if "mp3" in url.lower() else ".wav"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        print(f"   ❌ Network download failed for URL {url}: {str(e)}")
        return None

def backfill_sonic_vectors():
    db: Session = SessionLocal()
    try:
        # Wakes up SQLAlchemy mapping configuration
        _ = db.query(MediaPortfolio).first()

        users = db.query(User).all()
        print(f"Found {len(users)} total artists in database. Starting scan...")

        points = []
        for user in users:
            if not getattr(user, "portfolios", None):
                print(f"Skipping {user.artist_name} (No portfolio uploads found).")
                continue
                
            audio_track = next((item for item in user.portfolios if item.file_type == "audio"), None)
            if not audio_track:
                print(f"Skipping {user.artist_name} (No audio tracks found in portfolio).")
                continue
                
            file_path = audio_track.file_url
            temp_local_path = None

            # Check if the path is a web link pointing to your MinIO container
            if file_path.startswith("http://") or file_path.startswith("https://"):
                print(f"Fetching remote asset for {user.artist_name} from MinIO...")
                temp_local_path = download_temporary_audio(file_path)
            else:
                # Fallback to local file paths if any exist
                if os.path.exists(file_path):
                    temp_local_path = file_path

            if not temp_local_path:
                print(f"Could not resolve audio asset location for {user.artist_name}")
                continue

            print(f"Extracting traits for {user.artist_name} from '{audio_track.title}'...")
            vector = extract_audio_features(temp_local_path)
            
            # Clean up the temporary file immediately if we downloaded one
            if file_path.startswith("http://") and temp_local_path and os.path.exists(temp_local_path):
                os.remove(temp_local_path)
            
            if not vector:
                print(f"Failed feature extraction for {user.artist_name}")
                continue

            points.append(
                models.PointStruct(
                    id=user.id,
                    vector=vector,
                    payload={
                        "artist_id": user.id,
                        "artist_name": user.artist_name,
                        "role_type": user.role_type,
                        "tenant_id": user.tenant_id
                    }
                )
            )

        if points:
            print(f"Upserting {len(points)} sonic vectors into Qdrant collection...")
            qdrant_client.upsert(
                collection_name="artist_audio_radar",
                points=points
            )
            print("Backfill data sync pipeline complete!")
        else:
            print("No eligible audio assets found to backfill.")

    except Exception as e:
        print(f"Fatal run execution error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_sonic_vectors()