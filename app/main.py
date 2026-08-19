import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import engine, Base
from app.models.collab import CollabRequest
from app.models.media import MediaPortfolio
from app.routers import auth, marketplace, chat
from app.routers.media import router as media_router
from app.middleware.rate_limiter import RedisRateLimiterMiddleware
from app.core.qdrant_setup import init_audio_collection

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