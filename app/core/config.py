from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core Application Global Parameters
    PROJECT_NAME: str = "Artist Collaboration Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super_secure_jwt_token_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 Days activation window

    # Relational Database Connection Target (PostgreSQL Container)
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5433"
    POSTGRES_DB: str = "artist_collab_db"

    # AI Vector Database Connection Target (Qdrant Container)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "artist_signatures"

    # MinIO Object Storage Configuration
    STORAGE_ENDPOINT_URL: str = "http://localhost:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = ""
    STORAGE_BUCKET_NAME: str = "artist-portfolio-assets"

    # Distributed Cache Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # Dynamic Connection String Builder using the new Psycopg3 driver parameters
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # Gracefully handle empty passwords to prevent formatting malformations
        pass_str = f":{self.POSTGRES_PASSWORD}" if self.POSTGRES_PASSWORD else ""
        return f"postgresql+psycopg://{self.POSTGRES_USER}{pass_str}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Tell Pydantic to read and load variables from your local hidden .env file
    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True, 
        extra="ignore" # Prevents application crashes if extra variables exist in your .env
    )

settings = Settings()