"""
================================================================================
FILE: app/services/media_service.py
DESKRIPSI: Service untuk download dan manage media files
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 1
================================================================================

KONFIGURASI:
- UPLOAD_DIR = "uploads/" (buat jika belum ada)
- Generate filename: {timestamp}_{user_id}_{uuid}.{ext}

TODO [MEDIA-001]: download_telegram_media(file_id, bot_token) -> dict
Download file dari Telegram.

Langkah:
1. GET https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}
2. Parse response JSON, ambil result.file_path
3. GET https://api.telegram.org/file/bot{bot_token}/{file_path}
4. Determine mime_type dari extension
5. Generate unique filename
6. Save binary ke UPLOAD_DIR
7. Return:
   {
     "file_path": "uploads/...",
     "file_name": "original_name.jpg",
     "mime_type": "image/jpeg",
     "file_size": 12345
   }

TODO [MEDIA-002]: download_whatsapp_media(media_id, access_token) -> dict
Download file dari WhatsApp Cloud API.

Langkah:
1. GET https://graph.facebook.com/v17.0/{media_id}
   Headers: Authorization: Bearer {access_token}
2. Parse response, ambil "url"
3. GET {url} dengan header Authorization yang sama
4. Save binary ke UPLOAD_DIR
5. Return dict seperti MEDIA-001

TODO [MEDIA-003]: get_mime_type(file_path) -> str
Detect mime type dari file.

Opsi:
- Gunakan python-magic library
- Atau mapping sederhana dari extension

TODO [MEDIA-004]: cleanup_old_files(days=30)
Hapus file yang lebih tua dari X hari.
Untuk scheduled cleanup (opsional).

CATATAN:
- Gunakan httpx untuk async HTTP requests
- Handle timeout dan retry
- Log semua download untuk debugging
================================================================================
"""
