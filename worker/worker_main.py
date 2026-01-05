import logging
import json
from typing import Optional, List, Dict
from datetime import datetime

from app.db.connection import prisma
from worker.llm.llm_client import call_llm, LLMAPIError
from worker.llm.parser import parse_llm_response, ParserError
from worker.services.transaction_service import (
    save_transaction,
    save_ocr_result,
    TransactionServiceError
)
from worker.services.sanity_checks import run_sanity_checks
from worker.llm.prompts import build_prompt

from worker.ocr.preprocessor import ImagePreprocessor
from worker.utils.image_utils import load_image
from worker.ocr.tesseract import TesseractOCR

logger = logging.getLogger(__name__)


class WorkerError(Exception):
    pass


# TEXT MESSAGE - SUPPORTS MULTIPLE TRANSACTIONS
async def process_text_message(
    user_id: int,
    text: str,
    source: str = "telegram"
) -> Optional[List[Dict]]:
    """
    Process text message - can contain MULTIPLE transactions
    (Same as before - no changes needed)
    """
    try:
        logger.info(
            "Processing text message from user %s via %s",
            user_id,
            source
        )

        # 1. Build prompt for multiple transactions
        prompt = build_prompt(text, input_source="text")
        
        # 2. Call LLM
        llm_response = call_llm(prompt)
        llm_text = llm_response.get("text")
        if not llm_text:
            raise WorkerError("LLM mengembalikan teks kosong")

        logger.info("RAW LLM OUTPUT: %s", llm_text)

        # 3. Parse hasil LLM (returns list of transactions)
        parsed_transactions = parse_llm_response(llm_text)
        
        logger.info(f"Detected {len(parsed_transactions)} transaction(s)")

        # 4. Serialize usage metadata
        usage = llm_response.get("usage")
        llm_meta = {}
        if usage:
            llm_meta = {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }

        # 5. Process each transaction
        saved_transactions = []
        
        for i, parsed in enumerate(parsed_transactions):
            try:
                logger.info(f"Processing transaction {i+1}/{len(parsed_transactions)}")
                
                # Run sanity checks
                sanity = run_sanity_checks(parsed)
                
                # Save LLM response (one per transaction)
                llm_record = await prisma.llmresponse.create(
                    data={
                        "userId": user_id,
                        "inputSource": "text",
                        "inputText": text,
                        "promptUsed": prompt,
                        "modelName": llm_response.get("model"),
                        "llmOutput": llm_text,
                        "llmMeta": json.dumps({
                            **llm_meta,
                            "transaction_index": i,
                            "total_transactions": len(parsed_transactions)
                        }),
                        "createdAt": datetime.utcnow()
                    }
                )

                # Save transaction
                transaction = await save_transaction(
                    user_id=user_id,
                    amount=float(parsed["amount"]),
                    category=sanity.get("normalized_category", parsed["category"]),
                    description=parsed["note"],
                    transaction_type=parsed["intent"],
                    llm_response_id=llm_record.id,
                    receipt_id=None,
                    source=source
                )

                logger.info(f"✅ Transaction {i+1} saved: {transaction['id']}")
                saved_transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"❌ Failed to save transaction {i+1}: {e}", exc_info=True)
                continue

        if not saved_transactions:
            logger.error("No transactions were saved successfully")
            return None
        
        logger.info(f"✅ Successfully saved {len(saved_transactions)}/{len(parsed_transactions)} transactions")
        return saved_transactions

    except (LLMAPIError, ParserError, TransactionServiceError, WorkerError) as e:
        logger.error("Error processing text message: %s", e, exc_info=True)
        return None


# ✅ IMPROVED: IMAGE MESSAGE (OCR) with enhanced preprocessing
async def process_image_message(
    user_id: int,
    receipt_id: int,
    file_path: str,
    source: str
) -> Optional[dict]:
    """
    Process image message (OCR) - IMPROVED for various receipt conditions
    """
    try:
        logger.info(
            "Processing image message from user %s via %s",
            user_id,
            source
        )

        # 1. Load image
        img = load_image(file_path)
        logger.info(f"Image loaded: {img.shape}")

        # 2. Enhanced preprocessing dengan aggressive mode
        preprocessor = ImagePreprocessor(
            target_height=1600,  # Larger untuk detail lebih baik
            auto_deskew=True,
            denoise=True,
            aggressive_mode=True  # ✅ Enable untuk struk buruk
        )
        
        preprocessed_img = preprocessor.preprocess(img)
        logger.info("Preprocessing completed")

        # 3. Enhanced OCR dengan multiple PSM attempts
        ocr_engine = TesseractOCR(lang="ind+eng")
        ocr_text, ocr_metadata = ocr_engine.extract_text(preprocessed_img)

        if not ocr_text or len(ocr_text) < 10:
            logger.warning(f"OCR result too short: {len(ocr_text)} chars")
            raise WorkerError("OCR gagal mengekstrak teks yang cukup")

        logger.info(f"OCR SUCCESS: {len(ocr_text)} chars, confidence={ocr_metadata.get('confidence', 0):.1f}%")
        logger.info(f"OCR TEXT:\n{ocr_text}")

        # 4. Save OCR result
        await save_ocr_result(
            receipt_id=receipt_id,
            raw_text=ocr_text,
            confidence=ocr_metadata.get("confidence", 0.0)
        )

        # 5. Build prompt untuk OCR (dengan handling OCR errors)
        prompt = build_prompt(ocr_text, input_source="ocr")
        
        # 6. Call LLM
        llm_response = call_llm(prompt)
        llm_text = llm_response.get("text")
        
        if not llm_text:
            raise WorkerError("LLM mengembalikan teks kosong")

        logger.info("RAW LLM OUTPUT (OCR): %s", llm_text)

        # 7. Parse (take first transaction from list)
        parsed_transactions = parse_llm_response(llm_text)
        parsed = parsed_transactions[0]  # OCR: 1 struk = 1 transaksi
        
        # 8. Sanity check
        sanity = run_sanity_checks(parsed)

        # 9. Serialize usage + OCR metadata
        usage = llm_response.get("usage")
        llm_meta = {
            "ocr_confidence": ocr_metadata.get("confidence", 0.0),
            "ocr_word_count": ocr_metadata.get("word_count", 0),
            "ocr_char_count": ocr_metadata.get("char_count", 0),
            "ocr_psm_used": ocr_metadata.get("psm_used"),
            "ocr_attempts": ocr_metadata.get("attempts", [])
        }
        
        if usage:
            llm_meta.update({
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            })

        # 10. Save LLM response
        llm_record = await prisma.llmresponse.create(
            data={
                "userId": user_id,
                "inputSource": "ocr",
                "inputText": ocr_text,
                "promptUsed": prompt,
                "modelName": llm_response.get("model"),
                "llmOutput": llm_text,
                "llmMeta": json.dumps(llm_meta),
                "createdAt": datetime.utcnow()
            }
        )

        # 11. Save transaction
        transaction = await save_transaction(
            user_id=user_id,
            amount=float(parsed["amount"]),
            category=sanity.get("normalized_category", parsed["category"]),
            description=parsed["note"],
            transaction_type=parsed["intent"],
            llm_response_id=llm_record.id,
            receipt_id=receipt_id,
            source=source
        )

        logger.info(f"✅ Transaction from receipt saved: {transaction['id']}")
        return transaction

    except Exception as e:
        logger.error("Error processing image message: %s", e, exc_info=True)
        return None


# BACKGROUND WRAPPER
async def process_message_background(
    user_id: int,
    message_type: str,
    text: str = None,
    receipt_id: int = None,
    file_path: str = None,
    source: str = "telegram"
):
    """Background task wrapper"""
    if message_type == "text":
        await process_text_message(user_id, text, source)

    elif message_type == "image":
        await process_image_message(
            user_id, receipt_id, file_path, source
        )

    else:
        logger.error("Unknown message type: %s", message_type)