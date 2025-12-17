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


# TEXT MESSAGE

def process_text_message(
    user_id: int,
    text: str,
    source: str = "telegram"
) -> None:
    logger.info(
        "Processing text message from user %s via %s",
        user_id,
        source
    )

    try:
        llm_response = call_llm(text)

        llm_text = llm_response.get("text", "")
        if not llm_text:
            raise WorkerError("LLM mengembalikan teks kosong")

        logger.info("RAW LLM OUTPUT: %s", llm_text)

        parsed = parse_llm_response(llm_text)

        save_transaction(
            user_id=user_id,
            amount=float(parsed["amount"]),
            category=parsed["category"],
            description=parsed["note"],
            transaction_type=parsed["intent"],
            source=source,
            llm_response_id=None,
            receipt_id=None
        )




    except (LLMAPIError, ParserError, WorkerError) as e:
        logger.error("Error processing text message: %s", e)
        raise


# IMAGE MESSAGE (OCR)

async def process_image_message(
    user_id: int,
    receipt_id: int,
    file_path: str,
    source: str
) -> Optional[dict]:

    try:
        logger.info(f"Processing image message from user {user_id} via {source}")

        # --- Preprocess image ---
        preprocessor = ImagePreprocessor()
        img = load_image(file_path)
        preprocessed_img = preprocessor.preprocess(img)

        # --- OCR ---
        ocr_engine = TesseractOCR()
        ocr_text, ocr_metadata = ocr_engine.extract_text(preprocessed_img)

        if not ocr_text:
            raise WorkerError("OCR gagal mengekstrak teks")

        logger.info("OCR TEXT:\n%s", ocr_text)

        # --- Simpan OCR ---
        await save_ocr_result(
            receipt_id=receipt_id,
            raw_text=ocr_text,
            confidence=ocr_metadata.get("confidence", 0.0)
        )

        # Build prompt 
        prompt = build_prompt(ocr_text)

        # Call LLM 
        llm_response = call_llm(prompt)
        llm_text = llm_response.get("text", "")
        if not llm_text:
            raise WorkerError("LLM mengembalikan teks kosong")

        logger.info("RAW LLM OUTPUT (OCR): %s", llm_text)

        #  Parse 
        parsed = parse_llm_response(llm_text)

        # Sanity check 
        sanity = run_sanity_checks(parsed)

        #  Simpan LLM response 
        llm_record = await prisma.llmresponse.create(
            data={
                "userId": user_id,
                "inputSource": "ocr",
                "inputText": ocr_text,
                "promptUsed": prompt,
                "modelName": llm_response.get("model"),
                "llmOutput": json.dumps(llm_response),
                "llmMeta": json.dumps({
                    "ocr_confidence": ocr_metadata.get("confidence", 0.0)
                }),
                "createdAt": datetime.utcnow()
            }
        )

        # Simpan transaksi 
        transaction = await save_transaction(
            user_id=user_id,
            intent=parsed["intent"],
            amount=parsed["amount"],
            currency=parsed["currency"],
            category=sanity.get(
                "normalized_category",
                parsed["category"]
            ),
            note=parsed["note"],
            tx_date=parsed["date"],
            confidence=parsed["confidence"],
            llm_response_id=llm_record.id,
            receipt_id=receipt_id,
            source=source
        )

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
) -> None:

    try:
        if message_type == "text":
            process_text_message(user_id, text)
        elif message_type == "image":
            await process_image_message(
                user_id, receipt_id, file_path, source
            )
        else:
            logger.error("Unknown message type: %s", message_type)
    except Exception as e:
        logger.error("Background processing error: %s", e, exc_info=True)
