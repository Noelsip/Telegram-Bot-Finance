from contextlib import asynccontextmanager
from datetime import datetime
import logging
import subprocess
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from fastapi.routing import APIRoute

# Import Prisma client
from app.db import prisma, connect_db

# Import routers
from app.webhook import telegram_router, whatsapp_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

http_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client

    try:
        deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
        
        # ✅ FIX: Skip migrations di Railway (handled by entrypoint)
        if deployment_env == "railway":
            logger.info("🚂 Railway environment - migrations handled by entrypoint")
        else:
            logger.info("🔄 Running database migrations...")
            try:
                result = subprocess.run(
                    ["python", "-m", "prisma", "migrate", "deploy"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    logger.warning(f"⚠️  Migration warning: {result.stderr}")
                else:
                    logger.info("✅ Migrations completed")
            except subprocess.TimeoutExpired:
                logger.error("❌ Migration timeout after 60s")
            except Exception as e:
                logger.error(f"❌ Migration error: {e}")
        
        # Connect to database with retry
        logger.info("🔌 Connecting to database...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await connect_db()
                logger.info("✅ Database connected successfully")
                break
            except Exception as e:
                logger.error(f"❌ Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("❌ Failed to connect to database after all retries")
                    # Don't raise - let app start anyway for health check
                else:
                    import asyncio
                    await asyncio.sleep(2)
        
        # Initialize HTTP client
        http_client = httpx.AsyncClient(timeout=20.0)
        app.state.http_client = http_client
        logger.info("🌐 HTTP client initialized")
        
        logger.info("🚀 Application startup complete")

    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)

    yield
    
    # Cleanup
    logger.info("🛑 Shutting down...")
    if http_client:
        await http_client.aclose()
    try:
        await prisma.disconnect()
        logger.info("✅ Database disconnected")
    except:
        pass
    logger.info("♻️ Resources cleaned up")

# FastAPI app definition
app = FastAPI(
    title="Keuangan Bot API",
    version="2.0.0",
    lifespan=lifespan
)

# ✅ Health check - always return 200 if app is running
@app.get("/health")
async def health_check():
    """
    Health check endpoint - always returns 200 if app is running
    Database status is informational only
    """
    db_status = "unknown"
    user_count = 0
    
    # Try database, but don't fail health check if DB unavailable
    try:
        user_count = await prisma.user.count()
        db_status = "connected"
    except Exception as e:
        db_status = "disconnected"
        logger.warning(f"Health check: DB not available - {e}")
    
    # ✅ ALWAYS return 200 - Railway needs this to pass health check
    return JSONResponse(
        content={
            "status": "healthy",  # App is running = healthy
            "service": "keuangan-bot",
            "version": "2.0.0",
            "database": db_status,
            "users": user_count,
            "environment": os.getenv("DEPLOYMENT_ENV", "unknown"),
            "port": os.getenv("PORT", "8000"),
            "timestamp": datetime.now().isoformat()
        },
        status_code=200  # ✅ Always 200
    )
# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Keuangan Bot API",
        "version": "2.0.0",
        "status": "running",
        "port": os.getenv("PORT", "8000")
    }

# Include routers
app.include_router(telegram_router, tags=["Telegram"])  
app.include_router(whatsapp_router, prefix="/webhook/whatsapp", tags=["WhatsApp"])

@app.on_event("startup")
async def log_routes():
    logger.info("📋 Registered routes:")
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"  {route.path} {route.methods}")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException): 
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled Exception: {str(exc)} - Path: {request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal Server Error",
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
        },
    )