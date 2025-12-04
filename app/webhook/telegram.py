"""
================================================================================
FILE: app/webhook/telegram.py
DESKRIPSI: Telegram Webhook Handler
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 1
================================================================================

TODO [TG-001]: Setup Router
- Buat APIRouter instance
- Import dependencies: Request, HTTPException dari fastapi

TODO [TG-002]: POST / - Receive Webhook
Endpoint utama untuk menerima update dari Telegram.

Langkah-langkah:
1. Parse JSON body dari request
2. Extract informasi:
   - message.from.id -> user_id (BigInt)
   - message.from.username -> username
   - message.from.first_name -> display_name
   - message.message_id -> message_id
   - message.text -> text content (jika ada)
   - message.photo -> array photo (jika ada)
   - message.document -> document info (jika ada)

TODO [TG-003]: Handle User Registration
- Panggil user_service.get_or_create_user(user_id, username, display_name)
- User otomatis terdaftar saat pertama kali mengirim pesan

TODO [TG-004]: Handle Photo Message
Jika message.photo ada:
1. Ambil photo dengan resolusi tertinggi (index terakhir di array)
2. Panggil media_service.download_telegram_media(file_id, bot_token)
3. Simpan ke table receipts via receipt_service
4. Panggil worker process_image(user_id, receipt_id, file_path)
5. Return 200 OK

TODO [TG-005]: Handle Text Message
Jika message.text ada:
1. Langsung panggil worker process_text(user_id, text)
2. Return 200 OK

TODO [TG-006]: Send Reply to User
- Setelah processing selesai, kirim hasil ke user
- Gunakan Telegram Bot API: POST /sendMessage
- Format pesan: "✅ Transaksi tercatat: [kategori] Rp[amount]"
- Jika needs_review=True, tambahkan: "⚠️ Perlu review manual"

TODO [TG-007]: Error Handling
- Wrap semua logic dalam try-except
- Log error tapi tetap return 200 (agar Telegram tidak retry terus)
- Kirim pesan error ke user jika parsing gagal

CATATAN:
- Telegram akan retry webhook jika tidak dapat 200 dalam 60 detik
- Proses harus cepat, atau gunakan background task
- Bot token dari environment variable BOT_TOKEN

TELEGRAM FILE API:
- GET https://api.telegram.org/bot{token}/getFile?file_id={file_id}
- Response: {"result": {"file_path": "photos/file_123.jpg"}}
- Download: https://api.telegram.org/file/bot{token}/{file_path}
================================================================================
"""
import os
import httpx
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from app.config import BOT_TOKEN, TELEGRAM_API_URL
from app.services.user_service import user_service
from app.services.media_service import media_service
from app.services.receipt_service import receipt_service

router = APIRouter()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_telegram_message(chat_id: int, text: str):
    try:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

@router.post("/")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()

        message = body.get("message")
        if not message:
            return JSONResponse(status_code=200, content={"status": "ignored"})

        from_data = message.get("from", {})
        user_id = from_data.get("id")
        username = from_data.get("username")
        display_name = from_data.get("first_name", "")
        message_id = message.get("message_id")
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text")
        photos = message.get("photo")
        document = message.get("document")

        user = await user_service.get_or_create_user(
            user_id=user_id,
            username=username,
            display_name=display_name,
            source="telegram"
        )
        if photos:
            highest = photos[-1]
            file_id = highest.get("file_id")

            media_info = await media_service.download_telegram_media(
                file_id=file_id,
                bot_token=BOT_TOKEN
            )

            receipt = await receipt_service.create_receipt(
                user_id=user_id,
                file_path=media_info["file_path"],
                file_name=media_info["file_name"],
                mime_type=media_info["mime_type"],
                file_size=media_info["file_size"]
            )

            await send_telegram_message(chat_id, "Foto struk diterima. Sedang diproses.")

            return JSONResponse(status_code=200, content={"status": "photo_processed"})
        if text:
            await send_telegram_message(chat_id, "Pesan diterima. Sedang diproses.")
            return JSONResponse(status_code=200, content={"status": "text_processed"})

        return JSONResponse(status_code=200, content={"status": "ignored"})

    except Exception as e:
        print(f"Telegram Webhook Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=200,
            content={"status": "error_handled", "error": str(e)}
        )