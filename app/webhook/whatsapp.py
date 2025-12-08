import httpx
from fastapi import APIRouter, Request, Query, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from app.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_VERIFY_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_URL,
)
from app.db import prisma
from app.services import (
    user_service,
    media_service,
    receipt_service,
    get_transactions_for_period,
    build_history_summary,
)
from app.utils.helpers import parse_phone_number
from worker import process_text_message, process_image_message
from app.webhook.telegram import HELP_TEXT, detect_special_intent

router = APIRouter()


async def send_whatsapp_message(
    recipient_phone: str, message: str, client: httpx.AsyncClient
) -> None:
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
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")


async def handle_whatsapp_text_message(
    user_id: int,
    phone: str,
    text_body: str,
    client: httpx.AsyncClient,
):
    try:
        clean = text_body.strip()
        intent, period, direction = detect_special_intent(clean)

        if intent == "help":
            await send_whatsapp_message(phone, HELP_TEXT, client)
            return

        if intent == "history":
            if period == "today":
                txs, label = await get_transactions_for_period(
                    prisma=prisma,
                    user_id=user_id,
                    period="today",
                    direction=direction,
                )
            elif period == "week":
                txs, label = await get_transactions_for_period(
                    prisma=prisma,
                    user_id=user_id,
                    period="week",
                    direction=direction,
                )
            elif period == "month":
                txs, label = await get_transactions_for_period(
                    prisma=prisma,
                    user_id=user_id,
                    period="month",
                    direction=direction,
                )
            elif period == "year":
                txs, label = await get_transactions_for_period(
                    prisma=prisma,
                    user_id=user_id,
                    period="year",
                    direction=direction,
                )
            else:
                await send_whatsapp_message(
                    phone,
                    "Periode tidak didukung.",
                    client,
                )
                return

            summary = build_history_summary(label, txs)
            await send_whatsapp_message(phone, summary, client)
            return

        if intent == "export":
            await send_whatsapp_message(
                phone,
                "Fitur export Excel via WhatsApp belum tersedia. Silakan gunakan bot Telegram untuk menerima file Excel.",
                client,
            )
            return

        result = await process_text_message(
            user_id=user_id,
            text=clean,
            source="whatsapp",
        )

        if not result:
            await send_whatsapp_message(
                phone,
                "Maaf, aku tidak bisa memahami pesan ini sebagai transaksi.",
                client,
            )
            return

        amount = result.get("amount")
        category = result.get("category")
        direction = result.get("direction")

        lines = ["✅ Transaksi berhasil dicatat."]
        if amount is not None:
            lines.append(f"• Jumlah: Rp {amount:,.0f}")
        if category:
            lines.append(f"• Kategori: {category}")
        if direction:
            lines.append(f"• Tipe: {direction}")

        await send_whatsapp_message(
            phone,
            "\n".join(lines),
            client,
        )

    except Exception as e:
        print(f"Error in handle_whatsapp_text_message: {e}")
        await send_whatsapp_message(
            phone,
            "Terjadi error saat memproses transaksi. Coba lagi nanti.",
            client,
        )


async def process_whatsapp_receipt_background(
    user_id: int,
    phone: str,
    receipt_id: int,
    file_path: str,
    client: httpx.AsyncClient,
):
    try:
        result = await process_image_message(
            user_id=user_id,
            receipt_id=receipt_id,
            file_path=file_path,
            source="whatsapp",
        )

        if not result:
            await send_whatsapp_message(
                phone,
                "Struk sudah diproses, tapi aku belum bisa mengenali transaksinya. Coba kirim foto yang lebih jelas ya.",
                client,
            )
            return

        amount = result.get("amount")
        category = result.get("category")
        direction = result.get("direction")

        lines = ["✅ Transaksi dari struk berhasil dicatat."]
        if amount is not None:
            lines.append(f"• Jumlah: Rp {amount:,.0f}")
        if category:
            lines.append(f"• Kategori: {category}")
        if direction:
            lines.append(f"• Tipe: {direction}")

        await send_whatsapp_message(
            phone,
            "\n".join(lines),
            client,
        )

    except Exception as e:
        print(f"Error in process_whatsapp_receipt_background: {e}")
        await send_whatsapp_message(
            phone,
            "Terjadi error saat memproses struk. Coba lagi nanti.",
            client,
        )


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
                        prisma=prisma,
                        user_id=int(user_id),
                        username=None,
                        display_name=display_name,
                        source="whatsapp",
                    )

                    if message_type == "text":
                        text_body = message.get("text", {}).get("body")

                        if text_body:
                            print(
                                f"WhatsApp text - User: {user.id}, Message: {message_id}, Body: {text_body[:50]}"
                            )

                            # Deteksi intent dan proses langsung (tanpa worker) untuk help/history/export
                            # atau kirim ke worker untuk transaksi biasa
                            background_tasks.add_task(
                                handle_whatsapp_text_message,
                                int(user_id),
                                from_phone,
                                text_body,
                                client,
                            )

                    elif message_type == "image":
                        image_data = message.get("image", {})
                        media_id = image_data.get("id")

                        if media_id:
                            media_info = await media_service.download_whatsapp_media(
                                media_id=media_id,
                                access_token=WHATSAPP_ACCESS_TOKEN,
                                user_id=str(user.id),
                            )

                            receipt = await receipt_service.create_receipt(
                                prisma=prisma,
                                user_id=user.id,
                                file_path=media_info["file_path"],
                                file_name=media_info["file_name"],
                                mime_type=media_info["mime_type"],
                                file_size=media_info["file_size"],
                            )

                            print(
                                f"WhatsApp image - User: {user.id}, Receipt: {receipt.id}, Message: {message_id}"
                            )

                            await send_whatsapp_message(
                                from_phone,
                                "Foto struk diterima dan sedang diproses.",
                                client,
                            )

                            # Proses OCR + transaksi di background dan kirim ringkasan
                            background_tasks.add_task(
                                process_whatsapp_receipt_background,
                                int(user_id),
                                from_phone,
                                receipt.id,
                                media_info["file_path"],
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
            prisma=prisma,
            user_id=int(user_id),
            username=None,
            display_name=profile_name,
            source="whatsapp"
        )
        
        print(f"Twilio webhook - User: {user.id}, Body: {body[:50] if body else 'No text'}")

        if media_url:
            media_info = await media_service.download_twilio_media(media_url)

            receipt = await receipt_service.create_receipt(
                prisma=prisma,
                user_id=user.id,
                file_path=media_info["file_path"],
                file_name=media_info["file_name"],
                mime_type=media_info["mime_type"],
                file_size=media_info["file_size"],
            )
            
            print(f"Twilio media - User: {user.id}, Receipt: {receipt.id}")

        return PlainTextResponse(content="OK", status_code=200)

    except Exception as e:
        print(f"Twilio Webhook Error: {str(e)}")
        return PlainTextResponse(content="Error", status_code=200)
