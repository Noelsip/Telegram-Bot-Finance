import os
import httpx
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.config import BOT_TOKEN, TELEGRAM_API_URL
from app.services import user_service, media_service, receipt_service
from app.db import prisma 

router = APIRouter(tags=["Telegram"])

async def send_telegram_message(chat_id: int, text: str, client: httpx.AsyncClient):
    try:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        response = await client.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")


@router.post("/tg_webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()

        client: httpx.AsyncClient = request.app.state.http_client

        message = body.get("message")
        if not message:
            raise HTTPException(status_code=400, detail="No message in update")

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
            prisma=prisma,
            user_id=user_id,
            username=username,
            display_name=display_name,
            source="telegram"
        )
        
        if document:
            file_id = document.get("file_id")
            file_name = document.get("file_name", "document")
            
            media_info = await media_service.download_telegram_media(
                file_id=file_id,
                bot_token=BOT_TOKEN
            )
            
            receipt = await receipt_service.create_receipt(
                prisma=prisma,
                user_id=user.id,
                file_path=media_info["file_path"],
                file_name=media_info["file_name"],
                mime_type=media_info["mime_type"],
                file_size=media_info["file_size"]
            )
            
            await send_telegram_message(chat_id, "Dokumen diterima. Sedang diproses.", client)
            print(f"Document processed - User: {user.id}, Receipt: {receipt.id}, Message: {message_id}")
            
            return JSONResponse(status_code=200, content={"status": "document_processed"})
        
        if photos:
            highest = photos[-1]
            file_id = highest.get("file_id")

            media_info = await media_service.download_telegram_media(
                file_id=file_id,
                bot_token=BOT_TOKEN
            )

            receipt = await receipt_service.create_receipt(
                user_id=user.id,
                file_path=media_info["file_path"],
                file_name=media_info["file_name"],
                mime_type=media_info["mime_type"],
                file_size=media_info["file_size"]
            )

            await send_telegram_message(chat_id, "Foto struk diterima. Sedang diproses.", client)
            print(f"Photo processed - User: {user.id}, Receipt: {receipt.id}, Message: {message_id}")

            return JSONResponse(status_code=200, content={"status": "photo_processed"})
        if text:
            print(f"Text message - User: {user.id}, Message: {message_id}, Content: {text[:50]}")
            await send_telegram_message(chat_id, "Pesan diterima. Sedang diproses.", client)
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