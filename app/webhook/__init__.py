from .telegram import router as telegram_router
from .whatsapp import router as whatsapp_router

__all__ = [
    "telegram_router",
    "whatsapp_router",
]