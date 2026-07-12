import os
import uuid
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import UploadFile
from app.core.config import settings

class StorageService:
    def __init__(self):
        # Detect if we are running in the cloud on Render
        self.is_production = os.getenv("RENDER", "false").lower() == "true"
        self.bucket_name = settings.STORAGE_BUCKET_NAME

        if self.is_production:
            print("📦 Production Environment Detected: Using local filesystem fallback storage.")
            # Set up a directory inside the container to hold the audio assets
            self.local_storage_path = os.path.join(os.getcwd(), "static_uploads")
            os.makedirs(self.local_storage_path, exist_ok=True)
            self.s3_client = None
        else:
            print("Local Environment Detected: Initializing MinIO connection setup.")
            # Initialize the official AWS S3 client, but point it to our local MinIO server url
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.STORAGE_ENDPOINT_URL,
                aws_access_key_id=settings.MINIO_ROOT_USER,
                aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            )

            # AUTO-PROVISION SYSTEM BUCKET: Check if bucket exists, create it if missing
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                # 404 or specific S3 errors indicate the bucket does not exist yet
                if error_code in ['404', 'NoSuchBucket']:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    print(f"Unexpected storage bucket initialization check error: {e}")

    async def upload_audio_snippet(self, file: UploadFile) -> str:
        """
        Streams an incoming file directly into the local MinIO bucket (dev)
        or saves it directly to Render's filesystem disk space (prod).
        """
        try:
            # 1. Generate a completely unique filename using UUID to prevent collisions
            file_extension = file.filename.split(".")[-1] if "." in file.filename else "mp3"
            unique_filename = f"{uuid.uuid4()}.{file_extension}"

            # 2. Read the binary content of the file from memory
            file_content = await file.read()

            # Check if running on Render production
            if self.is_production:
                # Save the file directly onto the Render container local disk
                file_path = os.path.join(self.local_storage_path, unique_filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                
                # Return the path your frontend will hit (we will mount this as a static route)
                return f"/static/uploads/{unique_filename}"
            
            else:
                # 3. Stream the raw data directly into your Docker MinIO bucket
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=unique_filename,
                    Body=file_content,
                    ContentType=file.content_type  # e.g., "audio/mpeg"
                )

                # 4. Construct the standard address where this file can be streamed from
                file_url = f"{settings.STORAGE_ENDPOINT_URL}/{self.bucket_name}/{unique_filename}"
                return file_url

        except NoCredentialsError:
            raise RuntimeWarning("MinIO Storage Credentials missing or invalid.")
        except ClientError as e:
            raise RuntimeWarning(f"MinIO Engine Communication breakdown: {str(e)}")
        finally:
            # Reset the file pointer back to the beginning just to be safe
            await file.seek(0)

# Instantiate a global single instance of our storage engine
storage_service = StorageService()