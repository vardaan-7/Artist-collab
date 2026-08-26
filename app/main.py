import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.models.collab import CollabRequest
from app.models.media import MediaPortfolio
from app.routers import auth, marketplace, chat
from app.routers.media import router as media_router
from app.middleware.rate_limiter import RedisRateLimiterMiddleware
from app.core.qdrant_setup import init_audio_collection, qdrant_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Tables safely on boot
    try:
        await run_in_threadpool(Base.metadata.create_all, bind=engine)
        print("✅ Database schemas validated and ready.")
    except Exception as e:
        print(f"⚠️ Database initialization notice: {e}")

    # 2. Initialize Qdrant Collection without blocking event loop
    try:
        await run_in_threadpool(init_audio_collection)
    except Exception as e:
        print(f"🚨 Automatic Qdrant initialization failed on startup: {e}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Guard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter
override_redis_url = os.getenv("REDIS_URL") or getattr(settings, "REDIS_URL", "redis://localhost:6379")
app.add_middleware(
    RedisRateLimiterMiddleware, 
    redis_url=override_redis_url, 
    max_requests=60,
    window_seconds=60
)

# Architectural Domain Routers (Using consistent API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(marketplace.router, prefix=settings.API_V1_STR)
app.include_router(media_router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)

# Static File Mounting
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

if os.getenv("RENDER", "false").lower() == "true":
    os.makedirs("static_uploads", exist_ok=True)
    app.mount("/static/uploads", StaticFiles(directory="static_uploads"), name="production_uploads")

# Frontend Root Route
@app.get("/", tags=["Frontend"])
def read_index():
    return FileResponse(os.path.join("static", "index.html"))

# Health Diagnostic Probe
@app.get("/health", tags=["Health Check"])
def root_health_check():
    return {
        "status": "online",
        "message": f"Welcome to the {settings.PROJECT_NAME} API Engine Gateway.",
        "environment": "production" if os.getenv("RENDER", "false").lower() == "true" else "development"
    }

# Deep Multi-Service Heartbeat (Render + Supabase + Qdrant)
@app.get("/health/heartbeat", tags=["Health Check"])
def keep_alive_heartbeat(db: Session = Depends(get_db)):
    health_status = {
        "render": "alive",
        "database": "unreachable",
        "qdrant": "unreachable"
    }
    
    # 1. Ping Supabase (active SQL query resets 7-day pause timer)
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "active"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        
    # 2. Ping Qdrant Cloud (API read resets 7-day suspension timer)
    try:
        qdrant_client.get_collections()
        health_status["qdrant"] = "active"
    except Exception as e:
        health_status["qdrant"] = f"error: {str(e)}"
        
    return health_status