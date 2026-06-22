from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

class VectorStorageService:
    def __init__(self):
        # Connect to the running Qdrant Docker container
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        
        # Auto-provision the vector index collection on boot
        self.init_collection()

    def init_collection(self):
        """Creates the collection index if it doesn't exist yet"""
        try:
            # Check if collection already exists
            exists = self.client.collection_exists(collection_name=self.collection_name)
            
            if not exists:
                # 💡 Crucial Step: Define the math vector parameters
                # We'll use 128 dimensions (standard for compact audio/MFCC models) 
                # and Cosine distance to calculate similarity.
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=128, 
                        distance=models.Distance.COSINE
                    )
                )
                print(f"🚀 Qdrant Collection '{self.collection_name}' successfully provisioned!")
        except Exception as e:
            print(f"⚠️ Failed to initialize Qdrant client: {e}")

# Instantiate a global single instance of our vector storage engine
vector_service = VectorStorageService()