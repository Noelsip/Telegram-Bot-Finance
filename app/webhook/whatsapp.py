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

import httpx
from fastapi import APIRouter, Request, Query, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from app.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_URL
)
from app.services.user_service import user_service
from app.services.media_service import media_service
from app.services.receipt_service import receipt_service
from app.utils.helpers import parse_phone_number

router = APIRouter()


async def send_whatsapp_message(recipient_phone: str, message: str):
    try:
        url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": message}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return None


async def download_whatsapp_media(media_id: str) -> dict:
    try:
        url = f"{WHATSAPP_API_URL}/{media_id}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            media_data = response.json()

            media_url = media_data.get("url")
            mime_type = media_data.get("mime_type")

            if not media_url:
                raise Exception("Media URL missing")

            media_response = await client.get(media_url, headers=headers)
            media_response.raise_for_status()

            return await media_service.save_whatsapp_media(
                media_response.content,
                mime_type=mime_type,
                media_id=media_id
            )
    except Exception as e:
        print(f"Error downloading WhatsApp media: {str(e)}")
        raise


@router.get("/")
async def whatsapp_webhook_verify(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()

        if body.get("object") != "whatsapp_business_account":
            return JSONResponse(status_code=200, content={"status": "ignored"})

        entries = body.get("entry", [])
        if not entries:
            return JSONResponse(status_code=200, content={"status": "no_entries"})

        for entry in entries:
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                for message in messages:
                    from_phone = message.get("from")
                    message_type = message.get("type")

                    display_name = "WhatsApp User"
                    if contacts:
                        display_name = contacts[0].get("profile", {}).get("name", "WhatsApp User")

                    user_id = parse_phone_number(from_phone)

                    await user_service.get_or_create_user(
                        user_id=int(user_id),
                        username=None,
                        display_name=display_name,
                        source="whatsapp"
                    )

                    if message_type == "text":
                        text_body = message.get("text", {}).get("body")

                        if text_body:
                            await send_whatsapp_message(
                                from_phone,
                                "Pesan diterima dan sedang diproses."
                            )

                    elif message_type == "image":
                        image_data = message.get("image", {})
                        media_id = image_data.get("id")

                        if media_id:
                            media_info = await download_whatsapp_media(media_id)

                            await receipt_service.create_receipt(
                                user_id=int(user_id),
                                file_path=media_info["file_path"],
                                file_name=media_info["file_name"],
                                mime_type=media_info["mime_type"],
                                file_size=media_info["file_size"]
                            )

                            await send_whatsapp_message(
                                from_phone,
                                "Foto struk diterima dan sedang diproses."
                            )

                    else:
                        await send_whatsapp_message(
                            from_phone,
                            "Format pesan tidak didukung."
                        )

        return JSONResponse(status_code=200, content={"status": "success"})

    except Exception as e:
        print(f"WhatsApp Webhook Error: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={"status": "error_handled", "error": str(e)}
        )


@router.post("/twilio")
async def whatsapp_twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        form_data = await request.form()

        phone_raw = form_data.get("From", "")
        body = form_data.get("Body", "")
        media_url = form_data.get("MediaUrl0")
        profile_name = form_data.get("ProfileName", "WhatsApp User")

        phone_number = phone_raw.replace("whatsapp:", "")
        user_id = parse_phone_number(phone_number)

        await user_service.get_or_create_user(
            user_id=int(user_id),
            username=None,
            display_name=profile_name,
            source="whatsapp"
        )

        if media_url:
            media_info = await media_service.download_twilio_media(media_url)

            await receipt_service.create_receipt(
                user_id=int(user_id),
                file_path=media_info["file_path"],
                file_name=media_info["file_name"],
                mime_type=media_info["mime_type"],
                file_size=media_info["file_size"]
            )

        return PlainTextResponse(content="OK", status_code=200)

    except Exception as e:
        print(f"Twilio Webhook Error: {str(e)}")
        return PlainTextResponse(content="Error", status_code=200)
