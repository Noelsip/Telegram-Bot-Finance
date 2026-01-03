# Keuangan Bot - AI Coding Instructions

## Architecture Overview

This is a **financial tracking bot** for Telegram/WhatsApp that uses **OCR + LLM pipeline** to extract transactions from text messages and receipt images.

### Core Components

1. **`app/`** - FastAPI webhook server
   - `app/webhook/telegram.py` - Handles Telegram webhooks, commands (`/start`, `/history_harian`, `/export_mingguan`)
   - `app/webhook/whatsapp.py` - WhatsApp webhook handler
   - `app/services/` - User, media, receipt, transaction services for CRUD operations
   - FastAPI lifespan runs Prisma migrations on startup

2. **`worker/`** - Background processing pipeline
   - `worker/worker_main.py` - **Core entry point**: `process_text_message()`, `process_image_message()`
   - `worker/ocr/` - Image preprocessing (OpenCV) + Tesseract OCR extraction
   - `worker/llm/` - LLM client (currently Groq), parser, prompt builder
   - `worker/services/` - Transaction save, OCR save, sanity checks
   - Pipeline: OCR → LLM → Parse → Sanity Check → Save to DB

3. **Database (Prisma + PostgreSQL)**
   - Schema: `User` → `Receipt` → `OcrText`, `LlmResponse`, `Transaction`
   - Key relationship: `Transaction` references `LlmResponse` (for FK tracking) and optionally `Receipt`
   - All models use `userId` as BigInt (Telegram chat ID)

## Critical Workflows

### Database Management
```bash
# Generate Prisma client after schema changes
npm run prisma:generate

# Apply migrations (use Railway or Docker)
python -m prisma migrate deploy

# View data in Prisma Studio
npm run prisma:studio
```

### Running Locally
```bash
# Start with Docker (includes PostgreSQL)
docker-compose up --build

# Or run manually (requires local PostgreSQL)
python -m uvicorn app.main:app --reload
```

### Testing Worker Pipeline
```bash
# Manual testing script
python scripts/test_worker_manual.py

# OCR testing
python scripts/test_ocr.py
```

## Project-Specific Conventions

### LLM Response Handling
- **CRITICAL**: LLM returns JSON string, must be stored as STRING in `LlmResponse.llmOutput`
- Parse JSON with `parse_llm_response()` in `worker/llm/parser.py`
- Always serialize `usage` metadata to dict before saving to `llmMeta` JSON column
- Never pass raw objects to Prisma JSON fields

Example from `worker_main.py`:
```python
# ✅ CORRECT
llm_record = await prisma.llmresponse.create(
    data={
        "llmOutput": llm_text,                 # STRING only
        "llmMeta": json.dumps(llm_meta),       # Serialized dict
    }
)
```

### Transaction Intent Mapping
- User input: "masuk" / "keluar" / "gaji" / "bayar" (Indonesian)
- Normalized in LLM: `"income"` or `"expense"`
- Store in DB: use normalized values
- Categories: `["makan", "minuman", "belanja", "transportasi", "tagihan", "hiburan", "kesehatan", "pendidikan", "gaji", "transfer", "lainnya"]`

### Image Processing Pipeline
1. Upload → save to `upload/receipts/` or `upload/temp/`
2. Load with `load_image()` from `worker/utils/image_utils.py`
3. Preprocess with `ImagePreprocessor()` (grayscale, denoise, threshold)
4. OCR with `TesseractOCR()` (Indonesian + English)
5. Save raw OCR to `OcrText` table
6. Build prompt with `build_prompt()` in `worker/llm/prompts.py`
7. Call LLM → parse → save transaction

### Error Handling
- Custom exceptions: `LLMAPIError`, `ParserError`, `TransactionServiceError`
- Worker functions return `Optional[dict]` - `None` on error
- Always log errors with `logger.error(..., exc_info=True)`
- Sanity checks in `worker/services/sanity_checks.py` validate categories, amounts, dates

## Integration Points

### LLM Provider (Current: Groq, Target: OpenAI GPT-4o Mini)
- Client in `worker/llm/llm_client.py` - singleton pattern with `_get_client()`
- To switch providers: update `call_llm()`, adjust prompt format, update environment variables
- Current model: `llama-3.1-8b-instant` (Groq)

### Deployment
- **Docker**: Uses `Dockerfile` + `docker-compose.yml` (PostgreSQL + app)
- **Railway**: Deploy with `Procfile` - runs migrations on startup via `app/main.py` lifespan
- Database URL from environment: `DATABASE_URL`
- Required env vars: `BOT_TOKEN`, `DATABASE_URL`, `GROQ_API_KEY` (or `OPENAI_API_KEY` for future)

### Webhook Registration
- Telegram: Set webhook to `https://your-domain/webhook/telegram`
- WhatsApp: Set webhook to `https://your-domain/webhook/whatsapp`

## Key Files to Reference

- [worker_main.py](worker/worker_main.py) - Main processing logic
- [llm_client.py](worker/llm/llm_client.py) - LLM integration
- [telegram.py](app/webhook/telegram.py) - Command parsing, intent detection
- [schema.prisma](prisma/schema.prisma) - Database schema
- [transaction_service.py](worker/services/transaction_service.py) - DB save operations

## Common Gotchas

1. **Prisma JSON fields**: Always serialize Python dicts with `json.dumps()` before saving
2. **Tesseract**: Requires system installation (`apt-get install tesseract-ocr tesseract-ocr-ind`)
3. **Railway deployment**: Migrations run automatically in lifespan, don't run manually
4. **BigInt IDs**: Telegram chat IDs are BigInt, not regular Int
5. **Async everywhere**: All DB operations and worker functions are async
