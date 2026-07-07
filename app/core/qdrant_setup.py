from qdrant_client import QdrantClient
from qdrant_client.http import models

# 1. Connect to your active Qdrant Docker container
qdrant_client = QdrantClient(host="localhost", port=6333)

def init_audio_collection():
    collection_name = "artist_audio_radar"
    
    # 2. Check if this cabinet already exists so we don't accidentally wipe it
    existing_collections = qdrant_client.get_collections().collections
    exists = any(c.name == collection_name for c in existing_collections)
    
    if not exists:
        print(f"Creating collection '{collection_name}' inside Qdrant...")
        
        # 3. Explicitly tell Qdrant what kind of data to expect
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=33,  # Must perfectly match our 33 acoustic numbers!
                distance=models.Distance.COSINE  # Uses vector angles to find matching musical vibes
            )
        )
        print("Layer 2 Storage Cabinet initialized successfully!")
    else:
        print(f"Cabinet '{collection_name}' already exists. Ready for use.")

if __name__ == "__main__":
    init_audio_collection()