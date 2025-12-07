import os
import httpx
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.config import BOT_TOKEN, TELEGRAM_API_URL
from app.services import user_service, media_service, receipt_service
from app.db import prisma 
from worker import process_text_message, process_message_background
from app.services import (
    user_service,
    media_service,
    receipt_service,
    get_transactions_for_period,
    build_history_summary,
    create_excel_report,
)

HELP_TEXT = (
    "Selamat datang di Slip Ku 👋\n\n"
    "Aku bisa membantu kamu:\n"
    "• Mencatat pemasukan dan pengeluaran dari chat biasa\n"
    "• Melihat ringkasan transaksi harian & mingguan\n"
    "• Mengekspor riwayat transaksi mingguan, bulanan, dan tahunan ke Excel\n\n"
    "Contoh pesan transaksi:\n"
    "• makan siang 25rb\n"
    "• gaji bulan ini masuk 5jt\n"
    "• transfer ke teman 100rb\n\n"
    "Perintah:\n"
    "• /start atau /help – lihat pesan ini\n"
    "• /history_harian – ringkasan transaksi hari ini\n"
    "• /history_mingguan – ringkasan 7 hari terakhir\n"
    "• /export_mingguan – kirim file Excel 7 hari terakhir\n"
    "• /export_bulanan – kirim file Excel 30 hari terakhir\n"
    "• /export_tahunan – kirim file Excel 365 hari terakhir\n"
)

router = APIRouter(tags=["Telegram"])

async def send_telegram_message(chat_id: int, text: str, client: httpx.AsyncClient):
    try:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        response = await client.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

def detect_special_intent(text: str):
    s = text.strip().lower()
    if not s:
        return None, None
    s = s.lstrip("/")

    if s.startswith("start") or "help" in s or "bantuan" in s or "cara pakai" in s or "cara penggunaan" in s:
        return "help", None

    period = None
    if "hari ini" in s or "harian" in s or "today" in s:
        period = "today"
    elif "minggu" in s or "mingguan" in s or "7 hari" in s or "seminggu" in s:
        period = "week"
    elif "bulan" in s or "bulanan" in s or "30 hari" in s or "sebulan" in s:
        period = "month"
    elif "tahun" in s or "tahunan" in s or "365 hari" in s or "setahun" in s:
        period = "year"

    if "history" in s or "histori" in s or "riwayat" in s:
        if period is None:
            period = "week"
        return "history", period

    if "export" in s or "ekspor" in s or "laporan" in s or "report" in s or "excel" in s:
        if period is None:
            period = "month"
        return "export", period

    return None, None

async def handle_text_message(
    user_id: int,
    chat_id: int,
    text: str,
    client: httpx.AsyncClient,
):
    try:
        clean = text.strip()
        intent, period = detect_special_intent(clean)

        # 1) Command help / start
        if intent == "help":
            await send_telegram_message(chat_id, HELP_TEXT, client)
            return
 
        # 2) History harian
        if intent == "history" and period == "today":
            txs, label = await get_transactions_for_period(
                prisma=prisma,
                user_id=user_id,
                period="today",
            )
            summary = build_history_summary(label, txs)
            await send_telegram_message(chat_id, summary, client)
            return

        # 3) History mingguan
        if intent == "history" and period == "week":
            txs, label = await get_transactions_for_period(
                prisma=prisma,
                user_id=user_id,
                period="week",
            )
            summary = build_history_summary(label, txs)
            await send_telegram_message(chat_id, summary, client)
            return

        # 4) Export Excel mingguan
        if intent == "export" and period == "week":
            file_path, file_name = await create_excel_report(
                prisma=prisma,
                user_id=user_id,
                period="week",
            )
            if not file_path:
                await send_telegram_message(
                    chat_id,
                    "Belum ada transaksi dalam 7 hari terakhir, tidak ada file yang bisa diekspor.",
                    client,
                )
                return

            await send_telegram_document(
                chat_id,
                file_path,
                "Laporan transaksi mingguan (7 hari terakhir)",
                client,
            )
            return

        # 5) Export Excel bulanan
        if intent == "export" and period == "month":
            file_path, file_name = await create_excel_report(
                prisma=prisma,
                user_id=user_id,
                period="month",
            )
            if not file_path:
                await send_telegram_message(
                    chat_id,
                    "Belum ada transaksi dalam 30 hari terakhir, tidak ada file yang bisa diekspor.",
                    client,
                )
                return

            await send_telegram_document(
                chat_id,
                file_path,
                "Laporan transaksi bulanan (30 hari terakhir)",
                client,
            )
            return

        # 6) Export Excel tahunan
        if intent == "export" and period == "year":
            file_path, file_name = await create_excel_report(
                prisma=prisma,
                user_id=user_id,
                period="year",
            )
            if not file_path:
                await send_telegram_message(
                    chat_id,
                    "Belum ada transaksi dalam 365 hari terakhir, tidak ada file yang bisa diekspor.",
                    client,
                )
                return

            await send_telegram_document(
                chat_id,
                file_path,
                "Laporan transaksi tahunan (365 hari terakhir)",
                client,
            )
            return

        # 7) Bukan command -> anggap sebagai teks transaksi biasa
        result = await process_text_message(
            user_id=user_id,
            text=text,
            source="telegram",
        )

        if not result:
            await send_telegram_message(
                chat_id,
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

        await send_telegram_message(
            chat_id,
            "\n".join(lines),
            client,
        )

    except Exception as e:
        print(f"Error in handle_text_message: {e}")
        await send_telegram_message(
            chat_id,
            "Terjadi error saat memproses transaksi. Coba lagi nanti.",
            client,
        )

async def send_telegram_document(
    chat_id: int,
    file_path: str,
    caption: str,
    client: httpx.AsyncClient,
):
    try:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendDocument"
        with open(file_path, "rb") as f:
            files = {"document": ("report.xlsx", f)}
            data = {"chat_id": chat_id, "caption": caption}
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram document: {str(e)}")

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
            
            # Balasan cepat
            await send_telegram_message(chat_id, "Dokumen diterima. Sedang diproses.", client)
            print(f"Document processed - User: {user.id}, Receipt: {receipt.id}, Message: {message_id}")

            # Proses OCR + transaksi di background
            background_tasks.add_task(
                process_message_background,
                user.id,              
                "image",              
                None,                 
                receipt.id,           
                media_info["file_path"],  
                "telegram",           
            )
            
            return JSONResponse(status_code=200, content={"status": "document_processed"})
        
        if photos:
            highest = photos[-1]
            file_id = highest.get("file_id")

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

            # Balasan cepat
            await send_telegram_message(chat_id, "Foto struk diterima. Sedang diproses.", client)
            print(f"Photo processed - User: {user.id}, Receipt: {receipt.id}, Message: {message_id}")

            # Proses OCR + transaksi di background
            background_tasks.add_task(
                process_message_background,
                user.id,                  
                "image",                  
                None,                     
                receipt.id,               
                media_info["file_path"],  
                "telegram",               
            )

            return JSONResponse(status_code=200, content={"status": "photo_processed"})
        
        if text:
            print(f"Text message - User: {user.id}, Message: {message_id}, Content: {text[:50]}")

            intent, period = detect_special_intent(text)
            if intent in ("help", "history", "export"):
                await handle_text_message(
                    user.id,
                    chat_id,
                    text,
                    client,
                )

                return JSONResponse(status_code=200, content={"status": "command_processed"})

            await send_telegram_message(chat_id, "Pesan diterima. Sedang diproses.", client)

            background_tasks.add_task(
                handle_text_message,
                user.id,
                chat_id,
                text,
                client,
            )

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