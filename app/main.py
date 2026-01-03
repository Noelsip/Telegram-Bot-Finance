from contextlib import asynccontextmanager
from datetime import datetime
import logging
import subprocess

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
        # Jalankan migrasi database pertama-tama
        logger.info("Running database migrations...")
        subprocess.run(["python", "-m", "prisma", "migrate", "deploy"], check=True)
        
        # Connect to database
        logger.info("Connecting to database...")
        await connect_db()
        logger.info("✅ Database connected successfully")

        http_client = httpx.AsyncClient(timeout=20.0)
        app.state.http_client = http_client
        logger.info("🌐 HTTP client initialized")

    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise

    yield
    
    # Cleanup
    if http_client:
        await http_client.aclose()
    await prisma.disconnect()
    logger.info("♻️ Resources cleaned up")

app = FastAPI(
    title="Keuangan Bot API",
    version="2.0.0",
    lifespan=lifespan
)

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
        # Jalankan migrasi database pertama-tama
        logger.info("Running database migrations...")
        subprocess.run(["python", "-m", "prisma", "migrate", "deploy"], check=True)
        
        # Connect to database
        logger.info("Connecting to database...")
        await connect_db()
        logger.info("✅ Database connected successfully")

        http_client = httpx.AsyncClient(timeout=20.0)
        app.state.http_client = http_client
        logger.info("🌐 HTTP client initialized")

    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise

    yield
    
    # Cleanup
    if http_client:
        await http_client.aclose()
    await prisma.disconnect()
    logger.info("♻️ Resources cleaned up")

#Setup FastAPI app
app = FastAPI(
    title="Finance Tracker API",
    description="Telegram & WhatsApp Bot untuk tracking keuangan dengan OCR dan AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Health check endpoint untuk Railway
@app.get("/health")
async def health_check():
    """Health check endpoint untuk Railway monitoring"""
    try:
        # Test database connection
        await prisma.user.count()
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "keuangan-bot",
                "database": "connected",
                "timestamp": datetime.now().isoformat()
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )
        
app.include_router(telegram_router, tags=["Telegram"])  
app.include_router(whatsapp_router, prefix="/webhook/whatsapp", tags=["WhatsApp"])

@app.on_event("startup")
async def log_routes():
    logger.info("Registered routes:")
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