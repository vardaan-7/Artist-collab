import os
import re
from qdrant_client import QdrantClient
from qdrant_client.http import models

raw_url = os.getenv("QDRANT_URL", "http://localhost:6333").strip()
qdrant_api_key = os.getenv("QDRANT_API_KEY")

if "cloud.qdrant.io" in raw_url:
    # Strip schemes, ports, and trailing paths so we get just the hostname
    clean_host = raw_url.replace("https://", "").replace("http://", "")
    clean_host = re.sub(r":\d+.*$", "", clean_host).rstrip("/")

    print(f"🔌 Connecting to Qdrant Cloud Host: {clean_host} over HTTPS (Port 443)")
    qdrant_client = QdrantClient(
        host=clean_host,
        port=443,
        https=True,
        api_key=qdrant_api_key,
        timeout=10.0,
        prefer_grpc=False
    )
else:
    print(f"🔌 Connecting to local/custom Qdrant: {raw_url}")
    qdrant_client = QdrantClient(
        url=raw_url,
        api_key=qdrant_api_key,
        timeout=10.0
    )

def init_audio_collection():
    collection_name = "artist_audio_radar"
    try:
        collections_response = qdrant_client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]
        
        if collection_name not in existing_collections:
            print(f"Creating collection '{collection_name}' inside Qdrant Cloud...")
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