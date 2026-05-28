from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core Application Global Parameters
    PROJECT_NAME: str = "Artist Collaboration Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super_secure_jwt_token_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 Days activation window

    # Relational Database Connection Target (PostgreSQL Container)
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "supersecretpassword"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5433"
    POSTGRES_DB: str = "artist_collab_db"

    # AI Vector Database Connection Target (Qdrant Container)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    #minio
    STORAGE_ENDPOINT_URL: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "admin"
    STORAGE_SECRET_KEY: str = "supersecretstorageminiorootpassword"
    STORAGE_BUCKET_NAME: str = "artist-portfolio-assets"

    # Dynamic Connection String Builder using the new Psycopg3 driver parameters
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Tell Pydantic to read and load variables from your local hidden .env file
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()