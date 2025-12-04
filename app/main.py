"""
================================================================================
FILE: app/main.py
DESKRIPSI: FastAPI Entry Point - Webhook Gateway
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 1
================================================================================

TODO [MAIN-001]: Setup FastAPI Application
- Import FastAPI, CORSMiddleware
- Buat instance FastAPI dengan title="Finance Tracker API"
- Tambahkan CORS middleware (allow all origins untuk development)

TODO [MAIN-002]: Prisma Client Lifecycle
- Import Prisma dari prisma client
- Buat lifespan context manager:
  - Pada startup: await prisma.connect()
  - Pada shutdown: await prisma.disconnect()
- Attach lifespan ke FastAPI app

TODO [MAIN-003]: Mount Webhook Routers
- Import router dari app.webhook.telegram
- Import router dari app.webhook.whatsapp
- Mount telegram router di prefix="/webhook/telegram"
- Mount whatsapp router di prefix="/webhook/whatsapp"

TODO [MAIN-004]: Health Check Endpoint
- GET /health -> return {"status": "ok", "timestamp": datetime.now()}
- GET /health/db -> test koneksi database, return status

TODO [MAIN-005]: Error Handlers
- Buat global exception handler
- Log semua errors ke console/file
- Return proper HTTP error responses

DEPENDENCIES:
- fastapi
- uvicorn
- prisma-client-py

COMMAND UNTUK RUN:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
================================================================================
"""
