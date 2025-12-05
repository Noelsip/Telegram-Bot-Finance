import httpx
from fastapi import APIRouter, Request, Query, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from app.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_URL,
)
from app.services import user_service, media_service, receipt_service
from app.utils.helpers import parse_phone_number

router = APIRouter()


async def send_whatsapp_message(
    recipient_phone: str, message: str, client: httpx.AsyncClient
):
    try:
        url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": message},
        }

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return None


async def download_whatsapp_media(
    media_id: str, client: httpx.AsyncClient
) -> dict:
    try:
        url = f"{WHATSAPP_API_URL}/{media_id}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

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
            media_id=media_id,
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
        client: httpx.AsyncClient = request.app.state.http_client
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
                    message_id = message.get("id")

                    user = await user_service.get_or_create_user(
                        user_id=int(user_id),
                        username=None,
                        display_name=display_name,
                        source="whatsapp"
                    )

                    if message_type == "text":
                        text_body = message.get("text", {}).get("body")

                        if text_body:
                            print(f"WhatsApp text - User: {user.id}, Message: {message_id}, Body: {text_body[:50]}")
                            await send_whatsapp_message(
                                from_phone,
                                "Pesan diterima dan sedang diproses.",
                                client,
                            )

                    elif message_type == "image":
                        image_data = message.get("image", {})
                        media_id = image_data.get("id")

                        if media_id:
                            media_info = await download_whatsapp_media(media_id, client)

                            receipt = await receipt_service.create_receipt(
                                user_id=user.id,
                                file_path=media_info["file_path"],
                                file_name=media_info["file_name"],
                                mime_type=media_info["mime_type"],
                                file_size=media_info["file_size"]
                            )
                            
                            print(f"WhatsApp image - User: {user.id}, Receipt: {receipt.id}, Message: {message_id}")

                            await send_whatsapp_message(
                                from_phone,
                                "Foto struk diterima dan sedang diproses.",
                                client,
                            )

                    else:
                        await send_whatsapp_message(
                            from_phone,
                            "Format pesan tidak didukung.",
                            client,
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

        user = await user_service.get_or_create_user(
            user_id=int(user_id),
            username=None,
            display_name=profile_name,
            source="whatsapp"
        )
        
        print(f"Twilio webhook - User: {user.id}, Body: {body[:50] if body else 'No text'}")

        if media_url:
            media_info = await media_service.download_twilio_media(media_url)

            receipt = await receipt_service.create_receipt(
                user_id=user.id,
                file_path=media_info["file_path"],
                file_name=media_info["file_name"],
                mime_type=media_info["mime_type"],
                file_size=media_info["file_size"]
            )
            
            print(f"Twilio media - User: {user.id}, Receipt: {receipt.id}")

        return PlainTextResponse(content="OK", status_code=200)

    except Exception as e:
        print(f"Twilio Webhook Error: {str(e)}")
        return PlainTextResponse(content="Error", status_code=200)
