"""
================================================================================
FILE: app/webhook/whatsapp.py
DESKRIPSI: WhatsApp Webhook Handler (Meta Cloud API / Twilio)
ASSIGNEE: @Backend
PRIORITY: MEDIUM
SPRINT: 2
================================================================================

TODO [WA-001]: Setup Router
- Buat APIRouter instance

TODO [WA-002]: GET / - Webhook Verification (Meta Cloud API)
Meta Cloud API memerlukan verifikasi webhook saat setup.

Query parameters:
- hub.mode -> harus "subscribe"
- hub.verify_token -> harus match dengan WHATSAPP_VERIFY_TOKEN di env
- hub.challenge -> return value ini jika verifikasi sukses

Langkah:
1. Check hub.mode == "subscribe"
2. Check hub.verify_token == os.getenv("WHATSAPP_VERIFY_TOKEN")
3. Jika valid, return hub.challenge sebagai plain text
4. Jika tidak valid, return 403 Forbidden

TODO [WA-003]: POST / - Receive Message (Meta Cloud API)
Struktur payload Meta Cloud API:
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "628123456789",
          "type": "text|image",
          "text": {"body": "..."},
          "image": {"id": "media_id", "mime_type": "..."}
        }],
        "contacts": [{"profile": {"name": "User Name"}}]
      }
    }]
  }]
}

Langkah:
1. Parse JSON body
2. Extract messages dari entry[0].changes[0].value.messages
3. Untuk setiap message:
   - user_id = message.from (nomor WA tanpa +)
   - display_name = contacts[0].profile.name
   - Jika type == "text": process_text(user_id, message.text.body)
   - Jika type == "image": download media lalu process_image

TODO [WA-004]: Download Media dari Meta Cloud API
Media WhatsApp tidak langsung tersedia sebagai URL.

Langkah:
1. GET https://graph.facebook.com/v17.0/{media_id}
   Headers: Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
   Response: {"url": "https://..."}
2. GET {url} dengan header Authorization yang sama
3. Save binary ke uploads/
4. Return file_path

TODO [WA-005]: POST /twilio - Receive Message (Twilio Alternative)
Jika menggunakan Twilio WhatsApp API, payload berbeda:
- Form data (bukan JSON)
- From: whatsapp:+628123456789
- Body: text message
- MediaUrl0: URL media (bisa diakses langsung dengan Twilio auth)

TODO [WA-006]: Send Reply via WhatsApp
Meta Cloud API:
POST https://graph.facebook.com/v17.0/{phone_number_id}/messages
Headers: Authorization: Bearer {token}
Body: {
  "messaging_product": "whatsapp",
  "to": "{recipient_phone}",
  "type": "text",
  "text": {"body": "Pesan balasan"}
}

ENVIRONMENT VARIABLES YANG DIBUTUHKAN:
- WHATSAPP_ACCESS_TOKEN: Token dari Meta Business
- WHATSAPP_VERIFY_TOKEN: Token untuk verifikasi webhook (buat sendiri)
- WHATSAPP_PHONE_NUMBER_ID: ID nomor WhatsApp Business

CATATAN:
- Meta Cloud API gratis untuk 1000 conversations/bulan
- Twilio berbayar tapi lebih mudah setup
- Pilih salah satu sesuai kebutuhan tim
================================================================================
"""
