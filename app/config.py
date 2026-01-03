import os
import logging
from typing import Literal

# Deteksi environment
DEPLOYMENT_ENV: Literal["railway", "vps", "docker", "development"] = os.getenv(
    "DEPLOYMENT_ENV", "development"
)

# Load .env hanya jika BUKAN Railway
if DEPLOYMENT_ENV != "railway" and not os.getenv("RAILWAY_ENVIRONMENT"):
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded .env file")

# Telegram Config (REQUIRED)
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org")

# ✅ WhatsApp Config (COMMENTED - Not used yet)
# WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
# WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
# WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/v17.0")

# Database Config (REQUIRED)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = os.getenv("DATABASE_URL")

# OpenAI Config (REQUIRED)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Environment-specific settings
IS_RAILWAY = DEPLOYMENT_ENV == "railway" or bool(os.getenv("RAILWAY_ENVIRONMENT"))
IS_VPS = DEPLOYMENT_ENV == "vps"
IS_DOCKER = DEPLOYMENT_ENV == "docker"
IS_DEVELOPMENT = DEPLOYMENT_ENV == "development"

# Logging level by environment
LOG_LEVEL = "INFO" if (IS_RAILWAY or IS_VPS) else "DEBUG"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ✅ FIX: Parse DATABASE_URL untuk display
def _parse_db_info():
    """Parse DATABASE_URL untuk logging display"""
    if not DATABASE_URL:
        return f"{DB_HOST}:{DB_PORT}/{DB_NAME or 'unknown'}"
    
    try:
        import re
        match = re.search(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
        if match:
            _, _, db_host, db_port, db_name = match.groups()
            return f"{db_host}:{db_port}/{db_name}"
        else:
            return DATABASE_URL[:50] + "..."
    except Exception:
        return "database"

# Print config on startup (hide sensitive data)
print("=" * 60)
print("🚀 Starting Keuangan Bot")
print(f"   Environment: {DEPLOYMENT_ENV}")
print(f"   OpenAI Model: {OPENAI_MODEL}")
print(f"   Database: {_parse_db_info()}")
print(f"   Log Level: {LOG_LEVEL}")
print(f"   Railway Mode: {IS_RAILWAY}")
print("=" * 60)

# Validate required variables
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN tidak ditemukan!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY tidak ditemukan!")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL tidak ditemukan!")

print("✅ Configuration validated")