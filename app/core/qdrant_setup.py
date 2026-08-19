import os
import re
from qdrant_client import QdrantClient
from qdrant_client.http import models

raw_url = os.getenv("QDRANT_URL", "").strip()
qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip() or None

# Clean the host
clean_host = raw_url.replace("https://", "").replace("http://", "")
clean_host = re.sub(r":\d+.*$", "", clean_host)
clean_host = clean_host.split("/")[0].strip()

print(f"🔌 [Qdrant Setup] Connecting to Host: '{clean_host}' | API Key Found: {bool(qdrant_api_key)}")

if clean_host and "cloud.qdrant.io" in clean_host:
    endpoint_url = f"https://{clean_host}:6333"
    print(f"📡 Using Qdrant Cloud URL: {endpoint_url}")
    qdrant_client = QdrantClient(
        url=endpoint_url,
        api_key=qdrant_api_key,
        timeout=10.0,
        prefer_grpc=False
    )
elif raw_url:
    qdrant_client = QdrantClient(
        url=raw_url,
        api_key=qdrant_api_key,
        timeout=10.0
    )
else:
    qdrant_client = QdrantClient(url="http://localhost:6333", timeout=5.0)

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

        # 🛑 BULLETPROOF FIX: Force-delete any corrupted indexes, then rebuild strictly
        indexes_to_create = [
            ("tenant_id", models.PayloadSchemaType.KEYWORD),
            ("artist_id", models.PayloadSchemaType.INTEGER),
        ]

        for field_name, schema_type in indexes_to_create:
            try:
                # 1. Wipe the old index if it exists (ignores errors if missing)
                qdrant_client.delete_payload_index(
                    collection_name=collection_name,
                    field_name=field_name
                )
            except Exception:
                pass 
                
            try:
                # 2. Recreate with the strict integer/keyword types
                qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=schema_type
                )
                print(f"✅ Hardened index established for: '{field_name}' ({schema_type})")
            except Exception as e:
                print(f"⚠️ Index creation skipped/failed for '{field_name}': {e}")

    except Exception as e:
        print(f"❌ Error handling Qdrant connection/initialization: {str(e)}")

if __name__ == "__main__":
    init_audio_collection()