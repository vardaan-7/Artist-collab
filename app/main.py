import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.rate_limiter import RedisRateLimiterMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth
from app.models.collab import CollabRequest
from app.routers import auth, marketplace

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
# This allows your future React or mobile frontend applications to safely talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # In production, swap "*" for your exact domain names
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RedisRateLimiterMiddleware, 
    redis_url="redis://localhost:6379", 
    max_requests=5, 
    window_seconds=60
)

# Register Application Architectural Domain Routers
# This plugs our route directly into the main running server instance
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(marketplace.router, prefix=settings.API_V1_STR)

#Mount the static directory to serve assets, CSS, or JS files
app.mount("/static", StaticFiles(directory="static"), name="static")


#Update Root Route to Serve the index.html Webpage
@app.get("/", tags=["Frontend"])
def read_index():
    """
    Serves the main single-page application interface for the artist portal.
    """
    return FileResponse(os.path.join("static", "index.html"))


#Relocated Health Check to /health so you don't lose it
@app.get("/health", tags=["Health Check"])
def root_health_check():
    """
    Core Root System Health Diagnostic Probe.
    """
    return {
        "status": "online",
        "message": f"Welcome to the {settings.PROJECT_NAME} API Engine Gateway.",
        "environment": "development"
    }