import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.rate_limiter import RedisRateLimiterMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.models.collab import CollabRequest
from app.models.media import MediaPortfolio
from app.routers import auth
from app.routers import marketplace
from app.routers.media import router as media_router

# Instruct SQLAlchemy to auto-create our tables if they don't exist yet
Base.metadata.create_all(bind=engine)

# Initialize the FastAPI Core Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",       # Swagger UI documentation endpoint path
    redoc_url="/redoc"      # Alternative ReDoc documentation endpoint path
)

# Mount Security CORS Middleware Guard Filters
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # In production, swap "*" for your exact domain names
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Redis connection configurations pulled dynamically from Pydantic Settings
app.add_middleware(
    RedisRateLimiterMiddleware, 
    redis_url=settings.REDIS_URL, # Swapped out hardcoded string for global settings param
    max_requests=5, 
    window_seconds=60
)

# Register Application Architectural Domain Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(marketplace.router, prefix=settings.API_V1_STR)
app.include_router(media_router, prefix=settings.API_V1_STR)

# Mount the static directory to serve assets, CSS, or JS files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the main single-page application interface for the artist portal
@app.get("/", tags=["Frontend"])
def read_index():
    return FileResponse(os.path.join("static", "index.html"))

# Core Root System Health Diagnostic Probe
@app.get("/health", tags=["Health Check"])
def root_health_check():
    return {
        "status": "online",
        "message": f"Welcome to the {settings.PROJECT_NAME} API Engine Gateway.",
        "environment": "development"
    }