import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333").strip().rstrip("/")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

# Initialize client with strict timeout and clean configuration
if qdrant_api_key:
    qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        timeout=10.0,
        prefer_grpc=False
    )
else:
    qdrant_client = QdrantClient(
        url=qdrant_url,
        timeout=10.0
    )

def init_audio_collection():
    collection_name = "artist_audio_radar"
    
    try:
        collections_response = qdrant_client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]
        
        if collection_name not in existing_collections:
            print(f"Creating collection '{collection_name}' inside Qdrant...")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=33,  
                    distance=models.Distance.COSINE  
                )
            )
            print(f"✅ Collection '{collection_name}' initialized successfully!")
        else:
            print(f"ℹ️ Cabinet '{collection_name}' already exists. Ready for use.")
    except Exception as e:
        print(f"❌ Error handling Qdrant connection/initialization: {str(e)}")

if __name__ == "__main__":
    init_audio_collection()