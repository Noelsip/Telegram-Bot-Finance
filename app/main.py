from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
import httpx

# Import Prisma client
from app.db import prisma, connect_db

# Import routers
from app.webhook.telegram import router as telegram_router

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
        logger.info(f"🚂 Starting in {deployment_env} environment")
        
        # Connect to database
        logger.info("🔌 Connecting to database...")
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                await connect_db()
                logger.info("✅ Database connected successfully")
                
                # Verify tables exist
                user_count = await prisma.user.count()
                logger.info(f"✅ Database schema verified - {user_count} users found")
                break
                
            except Exception as e:
                logger.error(f"❌ Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                import asyncio
                await asyncio.sleep(2)
        
        # Initialize HTTP client
        http_client = httpx.AsyncClient(timeout=30.0)
        app.state.http_client = http_client
        logger.info("🌐 HTTP client initialized")
        
        logger.info("🚀 Application startup complete")

    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise

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

# FastAPI app
app = FastAPI(
    title="Keuangan Bot API",
    version="2.0.0",
    lifespan=lifespan
)

# Health check
@app.get("/health")
async def health_check():
    db_status = "unknown"
    user_count = 0
    
    try:
        user_count = await prisma.user.count()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "keuangan-bot",
        "version": "2.0.0",
        "database": db_status,
        "users": user_count,
        "environment": os.getenv("DEPLOYMENT_ENV", "unknown"),
        "port": os.getenv("PORT", "8000")
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Keuangan Bot API",
        "version": "2.0.0",
        "status": "running"
    }

# ✅ FIX: Include Telegram router with correct prefix
app.include_router(telegram_router, prefix="/webhook", tags=["Telegram"])

# Log registered routes on startup
@app.on_event("startup")
async def log_routes():
    logger.info("📋 Registered routes:")
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"  {route.methods} {route.path}")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Internal Server Error"}
    )