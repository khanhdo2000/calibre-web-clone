from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.services.cache import cache_service
from app.services.calibre_watcher import calibre_watcher
from app.database import init_db
from app.routes import books, metadata, files, auth, user_features, admin, kindle_pair, kindle_simple

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Calibre Web Clone...")
    logger.info(f"Calibre library path: {settings.calibre_library_path}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Connect to Redis cache
    await cache_service.connect()

    # Start Calibre database watcher
    calibre_watcher.start()

    # Log configuration
    if settings.use_google_drive:
        logger.info("Google Drive storage enabled")
    if settings.use_s3_covers:
        logger.info("S3 cover storage enabled")

    yield

    # Shutdown
    logger.info("Shutting down...")
    calibre_watcher.stop()
    await cache_service.disconnect()


app = FastAPI(
    title="Calibre Web Clone",
    description="A scalable web interface for Calibre libraries",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(user_features.router)
app.include_router(books.router)
app.include_router(metadata.router)
app.include_router(files.router)
app.include_router(admin.router)
app.include_router(kindle_pair.router)
app.include_router(kindle_simple.router)


@app.get("/")
async def root(request: Request):
    """Root endpoint - redirects Kindle/Kobo devices to pairing page"""
    from fastapi.responses import RedirectResponse

    # Check User-Agent for Kindle or Kobo devices
    user_agent = request.headers.get("user-agent", "").lower()
    if "kindle" in user_agent or "kobo" in user_agent:
        return RedirectResponse(url="/kindle", status_code=302)

    return {
        "name": "Kho sach MND",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cache": cache_service.redis_client is not None
    }
