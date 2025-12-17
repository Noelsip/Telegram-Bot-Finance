import logging
import json
from typing import Optional
from datetime import datetime

from app.db.connection import prisma
from .llm.prompts import build_prompt
from .llm.llm_client import call_llm
from .llm.parser import parse_llm_response
from .services.sanity_checks import run_sanity_checks
from .services.transaction_service import (
    save_transaction,
    save_ocr_result,
    TransactionServiceError
)
from .ocr.preprocessor import ImagePreprocessor
from .utils.image_utils import load_image
from .ocr.tesseract import TesseractOCR

logger = logging.getLogger(__name__)

class WorkerError(Exception):
    """Custom exception untuk worker errors."""
    pass

async def process_text_message(
    user_id: int,
    text: str,
    source: str
) -> Optional[dict]:
    """
    Proses pesan text dari user
    
    Args:
        user_id: User ID
        text: Pesan teks dari user
        source: "telegram" atau "whatsapp"

    Returns:
        Transaction dict jika berhasil, None jika gagal
    """
    try:
        logger.info(f"Processing text message from user {user_id} via {source}")

        # Build prompt
        prompt = build_prompt(text)
        logger.debug(f"Built prompt: {prompt[:100]}...")
        
        # Call Gemini API
        gemini_response = call_llm(prompt)
        if not gemini_response or not gemini_response.get("text"):
            raise WorkerError("Failed to get response from Gemini API")
        
        # Parse LLM response
        parsed_data = parse_llm_response(gemini_response)
        if not parsed_data or not parsed_data.get("parse_success"):
            raise WorkerError("Failed to parse LLM response")
        
        # Run sanity checks
        sanity_result = run_sanity_checks(parsed_data)
        if sanity_result.get("needs_review"):
            logger.warning(f"Sanity check flagged: {sanity_result.get('warning')}")

        # Save LLM response
        llm_record = await prisma.llmresponse.create(
            data={
                "userId": user_id,
                "inputSource": "text",
                "inputText": text,
                "promptUsed": prompt,
                "modelName": gemini_response.get("model", "gemini-2.5-flash"),
                "llmOutput": json.dumps(gemini_response), 
                "llmMeta": json.dumps(gemini_response.get("usage", {})),
                "createdAt": datetime.now()
            }
        )
        
        # Save transaction
        transaction = await save_transaction(
            user_id=user_id,
            amount=float(parsed_data["amount"]),
            category=sanity_result.get("normalized_category", parsed_data.get("category", "lainnya")),
            description=parsed_data.get("note", ""),
            transaction_type=parsed_data["intent"],
            llm_response_id=llm_record.id,
            receipt_id=None,
            source=source
        )
        
        logger.info(f"Successfully processed text message. Transaction ID: {transaction['id']}")
        return transaction
        
    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}", exc_info=True)
        return None


async def process_image_message(
    user_id: int,
    receipt_id: int,
    file_path: str,
    source: str
) -> Optional[dict]:
    """
    Proses pesan gambar/receipt dari user
    
    Args:
        user_id: User ID
        receipt_id: Receipt ID dari tabel receipts
        file_path: Path ke file gambar
        source: "telegram" atau "whatsapp"

    Returns:
        Transaction dict jika berhasil, None jika gagal
    """
    try:
        logger.info(f"Processing image message from user {user_id} via {source}")
        
        # Preprocess image menggunakan class
        preprocessor = ImagePreprocessor()
        img = load_image(file_path)
        preprocessed_img = preprocessor.preprocess(img)
        
        # ✅ DEBUG: Save preprocessed image untuk debugging
        import cv2
        debug_path = file_path.replace('.jpg', '_preprocessed.jpg').replace('.png', '_preprocessed.png')
        cv2.imwrite(debug_path, preprocessed_img)
        logger.info(f"📸 Preprocessed image saved: {debug_path}")
        
        # Extract text using OCR        
        ocr_engine = TesseractOCR()
        ocr_text, ocr_metadata = ocr_engine.extract_text(preprocessed_img)
        
        # ✅ DEBUG: Log OCR result untuk debugging
        logger.info(f"\n{'='*60}\n📝 OCR RAW TEXT:\n{'='*60}\n{ocr_text}\n{'='*60}")
        logger.info(f"🎯 OCR Confidence: {ocr_metadata.get('confidence', 0.0):.2f}%")
        logger.info(f"📊 OCR Metadata: {ocr_metadata}")
        
        if not ocr_text:
            raise WorkerError("Failed to extract text from image")
        
        logger.debug(f"Extracted OCR text: {ocr_text[:100]}...")
        
        # Save OCR result
        ocr_record = await save_ocr_result(
            receipt_id=receipt_id,
            raw_text=ocr_text,
            confidence=ocr_metadata.get("confidence", 0.0)
        )
        
        #  Build prompt dengan OCR text
        prompt = build_prompt(ocr_text)
        
        #  Call Gemini API
        gemini_response = call_llm(prompt)
        if not gemini_response or not gemini_response.get("text"):
            raise WorkerError("Failed to get response from Gemini API")
        
        #  Parse response
        parsed_data = parse_llm_response(gemini_response)
        if not parsed_data or not parsed_data.get("parse_success"):
            raise WorkerError("Failed to parse LLM response")
        
        #  Run sanity checks
        sanity_result = run_sanity_checks(parsed_data)
        if sanity_result.get("needs_review"):
            logger.warning(f"Sanity check flagged: {sanity_result.get('warning')}")
        
        #  Save LLM response
        llm_meta_dict = gemini_response.get("usage", {}).copy()
        llm_meta_dict["ocr_confidence"] = ocr_metadata.get("confidence", 0.0)

        llm_record = await prisma.llmresponse.create(
            data={
                "userId": user_id,
                "inputSource": "ocr",
                "inputText": ocr_text,
                "promptUsed": prompt,
                "modelName": gemini_response.get("model", "gemini-2.5-flash"),
                "llmOutput": json.dumps(gemini_response),
                "llmMeta": json.dumps(llm_meta_dict),
                "createdAt": datetime.now()
            }
        )
        
        #  Save transaction
        transaction = await save_transaction(
            user_id=user_id,
            amount=float(parsed_data["amount"]),
            category=sanity_result.get("normalized_category", parsed_data.get("category", "lainnya")),
            description=parsed_data.get("note", ""),
            transaction_type=parsed_data["intent"],
            llm_response_id=llm_record.id,
            receipt_id=receipt_id,
            source=source
        )
        
        logger.info(f"Successfully processed image message. Transaction ID: {transaction['id']}")
        return transaction
        
    except Exception as e:
        logger.error(f"Error processing image message: {str(e)}", exc_info=True)
        return None


async def process_message_background(
    user_id: int,
    message_type: str,
    text: str = None,
    receipt_id: int = None,
    file_path: str = None,
    source: str = "telegram"
) -> None:
    """
    Background task wrapper untuk processing
    
    Args:
        user_id: User ID
        message_type: "text" atau "image"
        text: Pesan text (untuk tipe text)
        receipt_id: Receipt ID (untuk tipe image)
        file_path: Path file gambar (untuk tipe image)
        source: Sumber pesan
    """
    try:
        if message_type == "text":
            await process_text_message(user_id, text, source)
        elif message_type == "image":
            await process_image_message(user_id, receipt_id, file_path, source)
        else:
            logger.error(f"Unknown message type: {message_type}")
    except Exception as e:
        logger.error(f"Background processing error: {str(e)}", exc_info=True)