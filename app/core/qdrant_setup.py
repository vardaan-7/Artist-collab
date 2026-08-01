import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

if qdrant_api_key:
    qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key
    )
else:
    qdrant_client = QdrantClient(url=qdrant_url)

def init_audio_collection():
    collection_name = "artist_audio_radar"
    
    try:
        existing_collections = qdrant_client.get_collections().collections
        exists = any(c.name == collection_name for c in existing_collections)
        
        if not exists:
            print(f"Creating collection '{collection_name}' inside Qdrant...")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=33,  
                    distance=models.Distance.COSINE  
                )
            )
            print("Layer 2 Storage Cabinet initialized successfully!")
        else:
            print(f"Cabinet '{collection_name}' already exists. Ready for use.")
    except Exception as e:
        print(f"Error handling Qdrant connection/initialization: {str(e)}")

if __name__ == "__main__":
    init_audio_collection()