from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth

# Instruct SQLAlchemy to auto-create our tables if they don't exist yet
# When the server starts, this reads app/models/user.py and builds the table in Docker Postgres
Base.metadata.create_all(bind=engine)

#Initialize the FastAPI Core Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",       # Swagger UI documentation endpoint path
    redoc_url="/redoc"      # Alternative ReDoc documentation endpoint path
)

#Mount Security CORS Middleware Guard Filters
# This allows your future React or mobile frontend applications to safely talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, swap "*" for your exact domain names
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Application Architectural Domain Routers
# This plugs our /auth/register route directly into the main running server instance
app.include_router(auth.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health Check"])
def root_health_check():
    """
    Core Root System Health Diagnostic Probe.
    """
    return {
        "status": "online",
        "message": f"Welcome to the {settings.PROJECT_NAME} API Engine Gateway.",
        "environment": "development"
    }