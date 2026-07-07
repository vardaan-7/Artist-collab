from app.core.qdrant_setup import qdrant_client
from qdrant_client.http import models

def initialize_collections():
    collection_name = "artist_audio_radar"
    print(f"Checking for collection '{collection_name}' in Qdrant...")
    
    try:
        # Check if it already exists
        exists = qdrant_client.collection_exists(collection_name=collection_name)
        
        if exists:
            print(f"Collection '{collection_name}' already exists. Recreating it to sync schema...")
            qdrant_client.delete_collection(collection_name=collection_name)
            
        # Create the collection with 33 dimensions for our Librosa features
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=33,  # Matches our 33 acoustic feature dimensions exactly
                distance=models.Distance.COSINE  # Cosine similarity for matching matches
            )
        )
        print(f"🎯 Successfully created collection '{collection_name}' with 33 dimensions!")
        
    except Exception as e:
        print(f"❌ Failed to initialize Qdrant: {str(e)}")

if __name__ == "__main__":
    initialize_collections()