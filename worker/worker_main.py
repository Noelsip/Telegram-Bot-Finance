import logging
import json
from typing import Optional
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


# =========================
# TEXT MESSAGE
# =========================
async def process_text_message(
    user_id: int,
    text: str,
    source: str = "telegram"
) -> Optional[dict]:

    try:
        logger.info(
            "Processing text message from user %s via %s",
            user_id,
            source
        )

        # 1. Call LLM
        llm_response = call_llm(text)
        llm_text = llm_response.get("text")
        if not llm_text:
            raise WorkerError("LLM mengembalikan teks kosong")

        logger.info("RAW LLM OUTPUT: %s", llm_text)

        # 2. Parse hasil LLM
        parsed = parse_llm_response(llm_text)

        # 3. Serialize usage (WAJIB, agar JSON aman)
        usage = llm_response.get("usage")
        llm_meta = {}
        if usage:
            llm_meta = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }

        # 4. Simpan LLM response (UNTUK FK)
        llm_record = await prisma.llmresponse.create(
            data={
                "userId": user_id,
                "inputSource": "text",
                "inputText": text,
                "promptUsed": text,
                "modelName": llm_response.get("model"),
                "llmOutput": llm_text,                 # ✅ STRING ONLY
                "llmMeta": json.dumps(llm_meta),       # ✅ DICT ONLY
                "createdAt": datetime.utcnow()
            }
        )

        # 5. Simpan transaksi
        transaction = await save_transaction(
            user_id=user_id,
            amount=float(parsed["amount"]),
            category=parsed["category"],
            description=parsed["note"],
            transaction_type=parsed["intent"],
            llm_response_id=llm_record.id,
            receipt_id=None,
            source=source
        )

        logger.info("Transaction saved: %s", transaction["id"])
        return transaction

    except (LLMAPIError, ParserError, TransactionServiceError, WorkerError) as e:
        logger.error("Error processing text message: %s", e, exc_info=True)
        return None


# =========================
# IMAGE MESSAGE (OCR)
# =========================
async def process_image_message(
    user_id: int,
    receipt_id: int,
    file_path: str,
    source: str
) -> Optional[dict]:

    try:
        logger.info(
            "Processing image message from user %s via %s",
            user_id,
            source
        )

        # 1. Preprocess image
        preprocessor = ImagePreprocessor()
        img = load_image(file_path)
        preprocessed_img = preprocessor.preprocess(img)

        # 2. OCR
        ocr_engine = TesseractOCR()
        ocr_text, ocr_metadata = ocr_engine.extract_text(preprocessed_img)

        if not ocr_text:
            raise WorkerError("OCR gagal mengekstrak teks")

        logger.info("OCR TEXT:\n%s", ocr_text)

        # 3. Simpan OCR result
        await save_ocr_result(
            receipt_id=receipt_id,
            raw_text=ocr_text,
            confidence=ocr_metadata.get("confidence", 0.0)
        )

        # 4. Build prompt & call LLM
        prompt = build_prompt(ocr_text)
        llm_response = call_llm(prompt)

        llm_text = llm_response.get("text")
        if not llm_text:
            raise WorkerError("LLM mengembalikan teks kosong")

        logger.info("RAW LLM OUTPUT (OCR): %s", llm_text)

        # 5. Parse & sanity check
        parsed = parse_llm_response(llm_text)
        sanity = run_sanity_checks(parsed)

        # 6. Serialize usage
        usage = llm_response.get("usage")
        llm_meta = {
            "ocr_confidence": ocr_metadata.get("confidence", 0.0)
        }
        if usage:
            llm_meta.update({
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            })

        # 7. Simpan LLM response
        llm_record = await prisma.llmresponse.create(
            data={
                "userId": user_id,
                "inputSource": "ocr",
                "inputText": ocr_text,
                "promptUsed": prompt,
                "modelName": llm_response.get("model"),
                "llmOutput": llm_text,                 # ✅ STRING
                "llmMeta": json.dumps(llm_meta),       # ✅ JSON
                "createdAt": datetime.utcnow()
            }
        )

        # 8. Simpan transaksi
        transaction = await save_transaction(
            user_id=user_id,
            amount=float(parsed["amount"]),
            category=sanity.get(
                "normalized_category",
                parsed["category"]
            ),
            description=parsed["note"],
            transaction_type=parsed["intent"],
            llm_response_id=llm_record.id,
            receipt_id=receipt_id,
            source=source
        )

        return transaction

    except Exception as e:
        logger.error("Error processing image message: %s", e, exc_info=True)
        return None


# =========================
# BACKGROUND WRAPPER
# =========================
async def process_message_background(
    user_id: int,
    message_type: str,
    text: str = None,
    receipt_id: int = None,
    file_path: str = None,
    source: str = "telegram"
):

    if message_type == "text":
        await process_text_message(user_id, text, source)

    elif message_type == "image":
        await process_image_message(
            user_id, receipt_id, file_path, source
        )

    else:
        logger.error("Unknown message type: %s", message_type)
