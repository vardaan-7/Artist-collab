import os
import uuid
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.client import Config
from fastapi import UploadFile
from app.core.config import settings

class StorageService:
    def __init__(self):
        # 1. Detect environment
        self.is_production = os.getenv("RENDER", "false").lower() == "true"
        
        if self.is_production:
            print("📦 Production Environment Detected: Connecting to Supabase Cloud Storage.")
            # Read variables directly from Render's secure settings panel
            self.bucket_name = os.getenv("STORAGE_BUCKET_NAME", "artist-portfolio-assets") 
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                config=Config(
                    signature_version='s3v4',                  # ⚠️ Explicitly enforce V4 signing
                    s3={'addressing_style': 'path'},           # ⚠️ Required for Supabase routes
                    retries={'max_attempts': 3, 'mode': 'standard'}
                )
            )
        else:
            print("💻 Local Environment Detected: Initializing MinIO connection setup.")
            self.bucket_name = settings.STORAGE_BUCKET_NAME
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.STORAGE_ENDPOINT_URL,
                aws_access_key_id=settings.MINIO_ROOT_USER,
                aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            )

            # AUTO-PROVISION SYSTEM BUCKET (Local MinIO Only)
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code in ['404', 'NoSuchBucket']:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    print(f"Unexpected storage bucket initialization check error: {e}")

    async def upload_audio_snippet(self, file: UploadFile) -> str:
        """
        Streams an incoming file directly into Supabase (prod) or local MinIO (dev).
        """
        try:
            # 1. Generate a completely unique filename using UUID to prevent collisions
            file_extension = file.filename.split(".")[-1] if "." in file.filename else "mp3"
            unique_filename = f"{uuid.uuid4()}.{file_extension}"

            # 2. Read the binary content of the file from memory
            file_content = await file.read()

            # 3. Stream the raw data directly into the active S3-compatible bucket
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=file_content,
                ContentType=file.content_type  # e.g., "audio/mpeg"
            )

            # 4. Construct the public streaming URL string
            if self.is_production:
                # Extract the project reference ID safely from the endpoint URL
                # Splits 'https://vwydmlwfnkddekchurev.storage.supabase.co...' to get 'vwydmlwfnkddekchurev'
                endpoint = os.getenv("AWS_ENDPOINT_URL", "")
                project_id = endpoint.split("//")[1].split(".")[0]
                
                # Direct, un-intercepted public URL format for Supabase Storage
                return f"https://{project_id}.supabase.co/storage/v1/object/public/{self.bucket_name}/{unique_filename}"
            else:
                # Local fallback URL for your machine's MinIO server container
                return f"{settings.STORAGE_ENDPOINT_URL}/{self.bucket_name}/{unique_filename}"

        except NoCredentialsError:
            raise RuntimeWarning("Storage Credentials missing or invalid.")
        except ClientError as e:
            # 💡 CRUCIAL DEBUG LOG: This exposes the hidden error dictionary to your Render console!
            print(f"❌ SUPABASE CRASH LOG: {e.response}")
            
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'No message provided')
            
            raise RuntimeWarning(f"Storage Engine Communication breakdown: [{error_code}] {error_message}")
        finally:
            # Reset the file pointer back to the beginning just to be safe
            await file.seek(0)

# Instantiate a global single instance of our storage engine
storage_service = StorageService()