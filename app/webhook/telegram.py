"""
Updated Telegram Webhook Handler with LLM Intent Classification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replace keyword-based intent detection with full LLM classification.
"""

import os
import httpx
import logging
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.config import BOT_TOKEN, TELEGRAM_API_URL
from app.services import user_service, media_service, receipt_service
from app.db import prisma 
from worker import process_text_message, process_image_message
from app.services import (
    user_service,
    media_service,
    receipt_service,
    get_transactions_for_period,
    build_history_summary,
    create_excel_report,
)
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

# ✅ NEW: Import LLM intent classifier
from worker.llm.intent_classifier import classify_intent, UserIntent

HELP_TEXT = (
    "Selamat datang di Slip Ku 💰\n\n"
    "Aku bisa membantu kamu:\n"
    "• Mencatat pemasukan dan pengeluaran dari chat biasa\n"
    "• Mencatat MULTIPLE transaksi dalam satu pesan\n"
    "• Mencatat MULTIPLE struk sekaligus (kirim beberapa foto)\n"
    "• Melihat ringkasan transaksi harian & mingguan\n"
    "• Mengekspor riwayat transaksi ke Excel\n\n"
    "Contoh pesan transaksi:\n"
    "• makan siang 25rb\n"
    "• gaji bulan ini masuk 5jt\n"
    "• hari ini beli makan 50rb, kemarin beli rokok 20rb, gajian 500rb\n\n"
    "Perintah:\n"
    "• /start atau /help – lihat pesan ini\n"
    "• /history_harian – ringkasan transaksi hari ini\n"
    "• /history_mingguan – ringkasan 7 hari terakhir\n"
    "• /export_mingguan – kirim file Excel 7 hari terakhir\n"
    "• /export_bulanan – kirim file Excel 30 hari terakhir\n"
    "• /export_tahunan – kirim file Excel 365 hari terakhir\n"
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Media group storage (unchanged)
pending_media_groups: Dict[str, Dict] = defaultdict(dict)
MEDIA_GROUP_TIMEOUT = 2.0


async def send_telegram_message(chat_id: int, text: str, client: httpx.AsyncClient):
    """Send text message to Telegram user"""
    try:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        response = await client.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}", exc_info=True)


async def send_telegram_document(
    chat_id: int,
    file_path: str,
    caption: str,
    client: httpx.AsyncClient,
):
    """Send document file to Telegram user"""
    try:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendDocument"
        with open(file_path, "rb") as f:
            files = {"document": ("report.xlsx", f)}
            data = {"chat_id": chat_id, "caption": caption}
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending Telegram document: {e}", exc_info=True)


# ✅ FIXED: LLM-powered intent detection
async def detect_intent_llm(text: str) -> Dict:
    """
    Use LLM to classify user intent
    
    Returns:
        Dict dengan keys:
            - intent: UserIntent enum
            - confidence: float
            - period: Optional[str]
            - direction: Optional[str]
            - reason: str (FIXED: was 'reasoning')
    """
    try:
        result = await classify_intent(text)
        
        # ✅ FIX: Use 'reason' instead of 'reasoning'
        reason = result.get('reason', result.get('reasoning', 'No reason provided'))
        
        logger.info(
            f"Intent detected: {result['intent']} "
            f"(confidence: {result['confidence']:.2f}) - {reason}"
        )
        return result
    except Exception as e:
        logger.error(f"Intent classification failed: {e}", exc_info=True)
        # Fallback: assume transaction
        return {
            "intent": UserIntent.TRANSACTION,
            "confidence": 0.3,
            "period": None,
            "direction": None,
            "reason": "Fallback to transaction due to error"
        }


async def handle_text_message(
    user_id: int,
    chat_id: int,
    text: str,
    client: httpx.AsyncClient,
):
    """
    Handle text message with LLM intent classification
    """
    try:
        # ✅ STEP 1: Classify intent using LLM
        intent_result = await detect_intent_llm(text)
        
        intent = intent_result["intent"]
        period = intent_result.get("period", "today")
        direction = intent_result.get("direction")
        confidence = intent_result.get("confidence", 0.0)
        
        logger.info(
            f"Intent: {intent}, Period: {period}, Direction: {direction}, "
            f"Confidence: {confidence:.2f}"
        )
        
        # ✅ STEP 2: Route based on intent
        
        # HELP
        if intent == UserIntent.HELP:
            await send_telegram_message(chat_id, HELP_TEXT, client)
            return
        
        # HISTORY
        if intent == UserIntent.HISTORY:
            txs, label = await get_transactions_for_period(
                prisma=prisma,
                user_id=user_id,
                period=period or "today",
                direction=direction,
            )
            summary = build_history_summary(label, txs)
            await send_telegram_message(chat_id, summary, client)
            return
        
        # EXPORT
        if intent == UserIntent.EXPORT:
            file_path, file_name = await create_excel_report(
                prisma=prisma,
                user_id=user_id,
                period=period or "month",
            )
            
            if not file_path:
                period_text = {
                    "week": "7 hari terakhir",
                    "month": "30 hari terakhir",
                    "year": "365 hari terakhir"
                }.get(period, "periode ini")
                
                await send_telegram_message(
                    chat_id,
                    f"Belum ada transaksi dalam {period_text}, tidak ada file yang bisa diekspor.",
                    client,
                )
                return

            caption_text = {
                "week": "Laporan transaksi mingguan (7 hari terakhir)",
                "month": "Laporan transaksi bulanan (30 hari terakhir)",
                "year": "Laporan transaksi tahunan (365 hari terakhir)"
            }.get(period, "Laporan transaksi")

            await send_telegram_document(chat_id, file_path, caption_text, client)
            return
        
        # SMALL TALK
        if intent == UserIntent.SMALL_TALK:
            responses = {
                "hai": "Hai! Ada yang bisa aku bantu? 😊",
                "halo": "Halo! Ada yang bisa aku bantu? 😊",
                "terima kasih": "Sama-sama! 🙏",
                "thanks": "Sama-sama! 🙏",
                "ok": "Siap! Ada lagi yang bisa aku bantu?",
                "oke": "Siap! Ada lagi yang bisa aku bantu?",
                "mantap": "Terima kasih! 🎉"
            }
            
            # Simple response for small talk
            response = responses.get(text.lower().strip(), 
                                   "Halo! Ketik /help untuk lihat apa yang bisa aku lakukan 😊")
            
            await send_telegram_message(chat_id, response, client)
            return
        
        # UNKNOWN - Log but treat as transaction
        if intent == UserIntent.UNKNOWN:
            logger.warning(f"Unknown intent for text: {text[:50]}... (treating as transaction)")
        
        # ✅ STEP 3: TRANSACTION (default)
        # Process as transaction(s) - could be multiple!
        results = await process_text_message(
            user_id=user_id,
            text=text,
            source="telegram",
        )

        if not results:
            await send_telegram_message(
                chat_id,
                "❌ Maaf, aku tidak bisa memahami pesan ini sebagai transaksi. "
                "Ketik /help untuk lihat contoh.",
                client,
            )
            return

        # ✅ BUILD RESPONSE
        if len(results) == 1:
            tx = results[0]
            lines = ["✅ Transaksi berhasil dicatat."]
            if tx.get("amount") is not None:
                lines.append(f"• Jumlah: Rp {tx['amount']:,.0f}")
            if tx.get("category"):
                lines.append(f"• Kategori: {tx['category']}")
            if tx.get("intent"):
                direction_text = "Pemasukan" if tx['intent'] == "income" else "Pengeluaran"
                lines.append(f"• Tipe: {direction_text}")
        else:
            lines = [f"✅ Berhasil mencatat {len(results)} transaksi:\n"]
            
            total_income = sum(tx.get("amount", 0) for tx in results if tx.get("intent") == "income")
            total_expense = sum(tx.get("amount", 0) for tx in results if tx.get("intent") == "expense")
            
            for i, tx in enumerate(results, 1):
                emoji = "💰" if tx.get("intent") == "income" else "💸"
                amount = tx.get("amount", 0)
                category = tx.get("category", "lainnya")
                note = tx.get("note", "")
                
                lines.append(f"{i}. {emoji} Rp {amount:,.0f} - {category}")
                if note and len(note) > 0:
                    lines.append(f"   📝 {note[:50]}")
            
            lines.append("\n📊 Ringkasan:")
            if total_income > 0:
                lines.append(f"💰 Total Pemasukan: Rp {total_income:,.0f}")
            if total_expense > 0:
                lines.append(f"💸 Total Pengeluaran: Rp {total_expense:,.0f}")

        await send_telegram_message(chat_id, "\n".join(lines), client)

    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}", exc_info=True)
        await send_telegram_message(
            chat_id,
            "❌ Terjadi error saat memproses pesan. Coba lagi nanti.",
            client,
        )


# ✅ Receipt processing functions (unchanged from your code)
async def process_single_receipt(
    user_id: int,
    receipt_id: int,
    file_path: str,
) -> Optional[Dict]:
    """Process single receipt dan return result dict"""
    try:
        result = await process_image_message(
            user_id=user_id,
            receipt_id=receipt_id,
            file_path=file_path,
            source="telegram",
        )
        return result
    except Exception as e:
        logger.error(f"Error processing receipt {receipt_id}: {e}", exc_info=True)
        return None


async def process_multiple_receipts_background(
    user_id: int,
    chat_id: int,
    receipts: List[Dict],
    client: httpx.AsyncClient,
):
    """Process multiple receipts dan kirim 1 pesan gabungan"""
    try:
        logger.info(f"Processing {len(receipts)} receipts for user {user_id}")
        
        results = []
        errors = []
        
        for i, receipt_data in enumerate(receipts):
            receipt_id = receipt_data["receipt_id"]
            file_path = receipt_data["file_path"]
            
            logger.info(f"Processing receipt {i+1}/{len(receipts)}: {receipt_id}")
            
            result = await process_single_receipt(
                user_id=user_id,
                receipt_id=receipt_id,
                file_path=file_path,
            )
            
            if result:
                result["receipt_index"] = i + 1
                results.append(result)
            else:
                errors.append(i + 1)
        
        # Build combined response
        if not results and errors:
            await send_telegram_message(
                chat_id,
                f"❌ Gagal memproses {len(errors)} struk. Coba kirim foto yang lebih jelas.",
                client,
            )
            return
        
        if len(results) == 1:
            tx = results[0]
            lines = ["✅ Transaksi dari struk berhasil dicatat."]
            if tx.get("amount") is not None:
                lines.append(f"• Jumlah: Rp {tx['amount']:,.0f}")
            if tx.get("category"):
                lines.append(f"• Kategori: {tx['category']}")
            if tx.get("intent"):
                direction_text = "Pemasukan" if tx['intent'] == "income" else "Pengeluaran"
                lines.append(f"• Tipe: {direction_text}")
        else:
            lines = [f"✅ Berhasil mencatat {len(results)} transaksi dari struk:\n"]
            
            total_income = sum(tx.get("amount", 0) for tx in results if tx.get("intent") == "income")
            total_expense = sum(tx.get("amount", 0) for tx in results if tx.get("intent") == "expense")
            
            for i, tx in enumerate(results, 1):
                emoji = "💰" if tx.get("intent") == "income" else "💸"
                amount = tx.get("amount", 0)
                category = tx.get("category", "lainnya")
                note = tx.get("note", "")
                
                lines.append(f"{i}. {emoji} Rp {amount:,.0f} - {category}")
                if note and len(note) > 0:
                    note_short = note[:40] + "..." if len(note) > 40 else note
                    lines.append(f"   📝 {note_short}")
            
            lines.append("\n📊 Ringkasan:")
            if total_income > 0:
                lines.append(f"💰 Total Pemasukan: Rp {total_income:,.0f}")
            if total_expense > 0:
                lines.append(f"💸 Total Pengeluaran: Rp {total_expense:,.0f}")
            
            if errors:
                lines.append(f"\n⚠️ {len(errors)} struk gagal diproses")
        
        await send_telegram_message(chat_id, "\n".join(lines), client)
        logger.info(f"✅ Sent combined response for {len(results)} receipts")

    except Exception as e:
        logger.error(f"Error in process_multiple_receipts_background: {e}", exc_info=True)
        await send_telegram_message(
            chat_id,
            "❌ Terjadi error saat memproses struk. Coba lagi nanti.",
            client,
        )


async def process_media_group_after_delay(
    media_group_id: str,
    user_id: int,
    chat_id: int,
    client: httpx.AsyncClient,
    background_tasks: BackgroundTasks,
):
    """Tunggu sebentar lalu process semua images dalam media group"""
    await asyncio.sleep(MEDIA_GROUP_TIMEOUT)
    
    if media_group_id not in pending_media_groups:
        return
    
    group_data = pending_media_groups.pop(media_group_id, None)
    if not group_data or not group_data.get("receipts"):
        return
    
    receipts = group_data["receipts"]
    logger.info(f"Processing media group {media_group_id} with {len(receipts)} images")
    
    await process_multiple_receipts_background(
        user_id=user_id,
        chat_id=chat_id,
        receipts=receipts,
        client=client,
    )


async def process_receipt_background(
    user_id: int,
    chat_id: int,
    receipt_id: int,
    file_path: str,
    client: httpx.AsyncClient,
):
    """Process single receipt di background"""
    await process_multiple_receipts_background(
        user_id=user_id,
        chat_id=chat_id,
        receipts=[{"receipt_id": receipt_id, "file_path": file_path}],
        client=client,
    )


@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Main webhook endpoint for Telegram"""
    try:
        body = await request.json()
        client: httpx.AsyncClient = request.app.state.http_client

        message = body.get("message")
        if not message:
            return JSONResponse(status_code=200, content={"status": "no_message"})

        # Extract message data
        from_data = message.get("from", {})
        user_id = from_data.get("id")
        username = from_data.get("username")
        display_name = from_data.get("first_name", "")
        message_id = message.get("message_id")
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text")
        photos = message.get("photo")
        document = message.get("document")
        media_group_id = message.get("media_group_id")

        # Get or create user
        user = await user_service.get_or_create_user(
            prisma=prisma,
            user_id=user_id,
            username=username,
            display_name=display_name,
            source="telegram"
        )
        
        # HANDLE DOCUMENT
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
            
            await send_telegram_message(chat_id, "📄 Dokumen diterima. Sedang diproses...", client)
            logger.info(f"Document processed - User: {user.id}, Receipt: {receipt.id}")

            background_tasks.add_task(
                process_receipt_background,
                user.id,
                chat_id,
                receipt.id,
                media_info["file_path"],
                client,
            )
            
            return JSONResponse(status_code=200, content={"status": "document_processed"})
        
        # HANDLE PHOTO
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

            logger.info(f"Photo processed - User: {user.id}, Receipt: {receipt.id}, MediaGroup: {media_group_id}")

            if media_group_id:
                if media_group_id not in pending_media_groups:
                    pending_media_groups[media_group_id] = {
                        "user_id": user.id,
                        "chat_id": chat_id,
                        "receipts": [],
                        "timestamp": datetime.now(),
                        "notified": False,
                    }
                    
                    await send_telegram_message(
                        chat_id, 
                        "📸 Beberapa foto struk diterima. Sedang diproses...", 
                        client
                    )
                
                pending_media_groups[media_group_id]["receipts"].append({
                    "receipt_id": receipt.id,
                    "file_path": media_info["file_path"],
                })
                
                if len(pending_media_groups[media_group_id]["receipts"]) == 1:
                    background_tasks.add_task(
                        process_media_group_after_delay,
                        media_group_id,
                        user.id,
                        chat_id,
                        client,
                        background_tasks,
                    )
                
                return JSONResponse(status_code=200, content={"status": "photo_added_to_group"})
            
            else:
                await send_telegram_message(chat_id, "📸 Foto struk diterima. Sedang diproses...", client)
                
                background_tasks.add_task(
                    process_receipt_background,
                    user.id,
                    chat_id,
                    receipt.id,
                    media_info["file_path"],
                    client,
                )

                return JSONResponse(status_code=200, content={"status": "photo_processed"})
        
        # ✅ HANDLE TEXT MESSAGE (with LLM intent classification)
        if text:
            logger.info(f"Text message - User: {user.id}, Message: {message_id}, Content: {text[:100]}")

            # ✅ Process with LLM intent classification
            await send_telegram_message(chat_id, "💬 Pesan diterima. Sedang diproses...", client)

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
        logger.error(f"Telegram Webhook Error: {e}", exc_info=True)
        return JSONResponse(
            status_code=200,
            content={"status": "error_handled", "error": str(e)}
        )