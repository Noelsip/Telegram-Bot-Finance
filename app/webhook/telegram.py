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
