from datetime import datetime
from typing import Dict, Optional, Any
import logging
import json
from decimal import Decimal

from app.db.connection import prisma 

logger = logging.getLogger(__name__)


# Custom Exceptions
class TransactionServiceError(Exception):
    """Base exception untuk transaction service"""
    pass

class DatabaseSaveError(TransactionServiceError):
    """Error saat menyimpan ke database"""
    pass

async def save_transaction(
    user_id: int,
    amount: float,
    category: str,
    description: str,
    transaction_type: str,
    llm_response_id: int,
    receipt_id: Optional[int],
    source: str,
    db: Optional[Any] = None
) -> dict:
    """
    Simple save transaction untuk worker_main.py
    
    Args:
        user_id: User ID
        amount: Amount dalam float/Decimal
        category: Category string
        description: Deskripsi/note
        transaction_type: "masuk" atau "keluar"
        llm_response_id: ID dari llm_responses table
        receipt_id: ID dari receipts table (optional)
        source: "telegram" atau "whatsapp"
        db: Prisma client (optional)
    
    Returns:
        Dict dengan transaction data
    """
    db_client = db or prisma
    
    try:
        logger.debug(
            f"Saving transaction for user {user_id}: "
            f"type={transaction_type}, amount={amount}"
        )
        
        # Convert to Decimal if needed
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        
        # Create transaction
        transaction = await db_client.transaction.create(
            data={
                "userId": user_id,
                "amount": int(amount),
                "category": category,
                "note": description,
                "intent": transaction_type,
                "llmResponseId": llm_response_id,
                "receiptId": receipt_id,
                "currency": "IDR",
                "txDate": datetime.now(),
                "needsReview": False,
                "createdAt": datetime.now(),
                "extra": json.dumps({"source": source})
            }
        )
        
        logger.info(f"Transaction saved: id={transaction.id}")
        return {
            "id": transaction.id,
            "userId": transaction.userId,
            "amount": transaction.amount,
            "category": transaction.category,
            "note": transaction.note,
            "intent": transaction.intent,
            "currency": transaction.currency,
            "createdAt": transaction.createdAt.isoformat() if transaction.createdAt else None
        }
        
    except Exception as e:
        logger.error(f"Error saving transaction: {e}", exc_info=True)
        raise TransactionServiceError(f"Failed to save transaction: {e}") from e
    
async def save_ocr_result(
    receipt_id: int,
    raw_text: str,
    confidence: float,
    db: Optional[Any] = None
) -> dict:
    """
    Save OCR result untuk worker_main.py
    
    Args:
        receipt_id: Receipt ID
        raw_text: Raw OCR text
        confidence: OCR confidence score (0-100)
        db: Prisma client (optional)
    
    Returns:
        Dict dengan OCR text data
    """
    db_client = db or prisma
    
    try:
        logger.debug(f"Saving OCR text for receipt {receipt_id}")
        
        ocr_text = await db_client.ocrtext.create(
            data={
                "receiptId": receipt_id,
                "ocrRaw": raw_text,
                "ocrMeta": json.dumps({"confidence": confidence}),
                "createdAt": datetime.now()
            }
        )
        
        logger.info(f"OCR text saved: id={ocr_text.id}")
        return {
            "id": ocr_text.id,
            "receiptId": ocr_text.receiptId,
            "confidence": confidence,
            "createdAt": ocr_text.createdAt.isoformat() if ocr_text.createdAt else None
        }

        
    except Exception as e:
        logger.error(f"Error saving OCR result: {e}", exc_info=True)
        raise TransactionServiceError(f"Failed to save OCR result: {e}") from e

# Internal Helper Functions
async def _save_llm_response(db: Any, payload: Dict) -> Optional[int]:
    """
    Save LLM response ke database
    
    Args:
        db: Prisma client instance (or None)
        payload: {
            'user_id': int,
            'input_source': str,  # 'text' or 'ocr'
            'input_text': str,
            'prompt_used': str,
            'model': str,
            'llm_output': str,
            'llm_meta': Dict
        }
    
    Returns:
        LLM response ID (int) or None jika db=None
    
    Raises:
        DatabaseSaveError: Jika save gagal
    """
    if db is None:
        logger.warning("No DB client provided - skipping llm_response insert")
        return None
    
    try:
        logger.debug(f"Saving LLM response for user {payload['user_id']}")
        
        # Prisma create operation
        record = await db.llmresponse.create(
            data={
                "userId": payload["user_id"],
                "inputSource": payload.get("input_source", "text"),
                "inputText": payload["input_text"],
                "promptUsed": payload.get("prompt_used", ""),
                "modelName": payload.get("model", "gemini-2.5-flash"),
                "llmOutput": payload.get("llm_output", ""),
                "llmMeta": json.dumps(payload.get("llm_meta", {})),
                "createdAt": datetime.now()
            }
        )
        
        llm_id = record.id
        logger.info(f"LLM response saved: id={llm_id}")
        return llm_id
        
    except Exception as e:
        logger.error(f"Failed to save LLM response: {e}", exc_info=True)
        raise DatabaseSaveError(f"Failed to save LLM response: {e}") from e
    
async def _save_ocr_text(db: Any, payload: Dict) -> Optional[int]:
    """
    Save OCR text result ke database
    
    Args:
        db: Prisma client instance
        payload: {
            'receipt_id': int,
            'ocr_raw': str,
            'ocr_meta': Dict
        }
    
    Returns:
        OCR text ID or None
    """
    if db is None:
        logger.warning("No DB client provided - skipping ocr_text insert")
        return None
    
    try:
        logger.debug(f"Saving OCR text for receipt {payload['receipt_id']}")
        
        record = await db.ocrtext.create(
            data={
                "receiptId": payload["receipt_id"],
                "ocrRaw": payload["ocr_raw"],
                "ocrMeta": json.dumps(payload.get("ocr_meta", {})),
                "createdAt": datetime.now()
            }
        )
        
        ocr_id = record.id
        logger.info(f"OCR text saved: id={ocr_id}")
        return ocr_id
        
    except Exception as e:
        logger.error(f"Failed to save OCR text: {e}", exc_info=True)
        raise DatabaseSaveError(f"Failed to save OCR text: {e}") from e

async def _save_transaction(db: Any, payload: Dict) -> Optional[int]:
    """
    Save transaction ke database
    
    Args:
        db: Prisma client instance
        payload: {
            'user_id': int,
            'llm_response_id': Optional[int],
            'receipt_id': Optional[int],
            'intent': str,  # 'masuk' or 'keluar'
            'amount': Decimal,
            'currency': str,
            'tx_date': Optional[datetime],
            'category': str,
            'note': str,
            'status': str,  # 'confirmed', 'pending_review', 'rejected'
            'needs_review': bool,
            'extra': Dict
        }
    
    Returns:
        Transaction ID or None
    """
    if db is None:
        logger.warning("No DB client provided - skipping transaction insert")
        return None
    
    try:
        logger.debug(
            f"Saving transaction for user {payload['user_id']}: "
            f"intent={payload['intent']}, amount={payload['amount']}"
        )
        
        record = await db.transaction.create(
            data={
                "userId": payload["user_id"],
                "llmResponseId": payload.get("llm_response_id"),
                "receiptId": payload.get("receipt_id"),
                "intent": payload["intent"],
                "amount": payload["amount"],
                "currency": payload.get("currency", "IDR"),
                "txDate": payload.get("tx_date"),
                "category": payload["category"],
                "note": payload.get("note", ""),
                "status": payload.get("status", "confirmed"),
                "needsReview": payload.get("needs_review", False),
                "extra": json.dumps(payload.get("extra", {})),
                "createdAt": datetime.now(),
                "updatedAt": datetime.now()
            }
        )
        
        tx_id = record.id
        logger.info(
            f"Transaction saved: id={tx_id}, "
            f"intent={payload['intent']}, amount={payload['amount']}, "
            f"status={payload['status']}"
        )
        return tx_id
        
    except Exception as e:
        logger.error(f"Failed to save transaction: {e}", exc_info=True)
        raise DatabaseSaveError(f"Failed to save transaction: {e}") from e

def _parse_transaction_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse transaction date dari ISO string
    
    Args:
        date_str: ISO format date string (YYYY-MM-DD)
    
    Returns:
        datetime object or None
    """
    if not date_str:
        return None
    
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None


# Public API Functions
async def save_transaction_from_text(
    user_id: int,
    text: str,
    parsed_output: Dict,
    sanity_result: Dict,
    llm_metadata: Dict,
    db: Optional[Any] = None
) -> Dict:
    """
    Save transaction dari text input
    
    Full workflow:
    1. Save LLM response ke llm_responses table
    2. Save transaction ke transactions table
    3. Link keduanya via llmResponseId
    
    Args:
        user_id: Telegram/WhatsApp user ID (BigInt)
        text: Raw input text dari user
        parsed_output: Hasil dari parser.parse_llm_response()
            {
                'intent': str,
                'amount': Decimal,
                'category': str,
                'note': str,
                'date': str (ISO),
                'confidence': float,
                'raw_output': str
            }
        sanity_result: Hasil dari sanity_checks.run_sanity_checks()
            {
                'needs_review': bool,
                'flags': List[str],
                'adjusted_confidence': float,
                'warning': str,
                'normalized_category': str
            }
        llm_metadata: Metadata dari gemini_client.call_gemini()
            {
                'model': str,
                'finish_reason': str,
                'prompt_tokens': int,
                'completion_tokens': int,
                'total_tokens': int
            }
        db: Prisma client instance (optional, untuk testing)
    
    Returns:
        Dict {
            'transaction_id': int,
            'llm_response_id': int,
            'status': str,
            'needs_review': bool,
            'amount': Decimal,
            'category': str,
            'created_at': str (ISO)
        }
    
    Raises:
        TransactionServiceError: Jika terjadi error saat save
    """
    logger.info(f"Saving transaction from text for user {user_id}")
    
    try:
        # Step 1: Save LLM response
        llm_payload = {
            "user_id": user_id,
            "input_source": "text",
            "input_text": text,
            "prompt_used": llm_metadata.get("prompt_used", ""),
            "model": llm_metadata.get("model", "gemini-2.5-flash"),
            "llm_output": parsed_output.get("raw_output", ""),
            "llm_meta": {
                "finish_reason": llm_metadata.get("finish_reason"),
                "prompt_tokens": llm_metadata.get("prompt_tokens", 0),
                "completion_tokens": llm_metadata.get("completion_tokens", 0),
                "total_tokens": llm_metadata.get("total_tokens", 0)
            }
        }
        
        llm_response_id = await _save_llm_response(db, llm_payload)
        
        # Step 2: Parse transaction date
        tx_date = _parse_transaction_date(parsed_output.get("date"))
        
        # Step 3: Determine status
        tx_status = "pending_review" if sanity_result["needs_review"] else "confirmed"
        
        # Step 4: Save transaction
        tx_payload = {
            "user_id": user_id,
            "llm_response_id": llm_response_id,
            "receipt_id": None,  # Text input tidak punya receipt
            "intent": parsed_output["intent"],
            "amount": parsed_output["amount"],
            "currency": "IDR",
            "tx_date": tx_date,
            "category": sanity_result["normalized_category"],
            "note": parsed_output.get("note", ""),
            "status": tx_status,
            "needs_review": sanity_result["needs_review"],
            "extra": {
                "source": "text_input",
                "original_category": parsed_output.get("category"),
                "confidence": sanity_result["adjusted_confidence"],
                "raw_confidence": parsed_output.get("confidence", 0),
                "flags": sanity_result.get("flags", []),
                "warnings": sanity_result.get("warning", "")
            }
        }
        
        transaction_id = await _save_transaction(db, tx_payload)
        
        # Step 5: Build result
        result = {
            "transaction_id": transaction_id,
            "llm_response_id": llm_response_id,
            "status": tx_status,
            "needs_review": sanity_result["needs_review"],
            "amount": parsed_output["amount"],
            "category": sanity_result["normalized_category"],
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(
            f"Transaction saved successfully: "
            f"tx_id={transaction_id}, amount={parsed_output['amount']}, "
            f"status={tx_status}"
        )
        
        return result
        
    except DatabaseSaveError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving transaction from text: {e}", exc_info=True)
        raise TransactionServiceError(f"Failed to save transaction: {e}") from e

async def save_transaction_from_ocr(
    user_id: int,
    receipt_id: int,
    ocr_text: str,
    parsed_output: Dict,
    sanity_result: Dict,
    llm_metadata: Dict,
    ocr_metadata: Dict,
    db: Optional[Any] = None
) -> Dict:
    """
    Save transaction dari OCR result
    
    Full workflow:
    1. Save OCR text ke ocr_texts table
    2. Save LLM response ke llm_responses table
    3. Save transaction ke transactions table
    4. Link semua records
    
    Args:
        user_id: User ID
        receipt_id: Receipt ID dari receipts table
        ocr_text: Raw OCR text
        parsed_output: Hasil parser LLM (sama format dengan text)
        sanity_result: Hasil sanity checks
        llm_metadata: Metadata LLM call
        ocr_metadata: Metadata OCR
            {
                'confidence': float,
                'preprocessing_steps': List[str],
                'image_quality': str,
                'processing_time_ms': int
            }
        db: Prisma client instance (optional)
    
    Returns:
        Dict {
            'transaction_id': int,
            'llm_response_id': int,
            'ocr_text_id': int,
            'receipt_id': int,
            'status': str,
            'needs_review': bool,
            'amount': Decimal,
            'category': str,
            'ocr_confidence': float,
            'created_at': str (ISO)
        }
    
    Raises:
        TransactionServiceError: Jika terjadi error
    """
    logger.info(f"Saving transaction from OCR for user {user_id}, receipt {receipt_id}")
    
    try:
        # Step 1: Save OCR text
        ocr_payload = {
            "receipt_id": receipt_id,
            "ocr_raw": ocr_text,
            "ocr_meta": ocr_metadata
        }
        
        ocr_text_id = await _save_ocr_text(db, ocr_payload)
        
        # Step 2: Save LLM response (dengan OCR metadata)
        llm_payload = {
            "user_id": user_id,
            "input_source": "ocr",
            "input_text": ocr_text,
            "prompt_used": llm_metadata.get("prompt_used", ""),
            "model": llm_metadata.get("model", "gemini-2.5-flash"),
            "llm_output": parsed_output.get("raw_output", ""),
            "llm_meta": {
                **llm_metadata,
                "ocr_metadata": ocr_metadata  # Include OCR metadata
            }
        }
        
        llm_response_id = await _save_llm_response(db, llm_payload)
        
        # Step 3: Parse date
        tx_date = _parse_transaction_date(parsed_output.get("date"))
        
        # Step 4: Determine status (OCR lebih strict)
        ocr_confidence = ocr_metadata.get("confidence", 0)
        needs_review = (
            sanity_result["needs_review"] or 
            ocr_confidence < 60  # Low OCR confidence = needs review
        )
        tx_status = "pending_review" if needs_review else "confirmed"
        
        # Step 5: Save transaction
        tx_payload = {
            "user_id": user_id,
            "llm_response_id": llm_response_id,
            "receipt_id": receipt_id,  # Link ke receipt!
            "intent": parsed_output["intent"],
            "amount": parsed_output["amount"],
            "currency": "IDR",
            "tx_date": tx_date,
            "category": sanity_result["normalized_category"],
            "note": parsed_output.get("note", ""),
            "status": tx_status,
            "needs_review": needs_review,
            "extra": {
                "source": "ocr_receipt",
                "original_category": parsed_output.get("category"),
                "confidence": sanity_result["adjusted_confidence"],
                "raw_confidence": parsed_output.get("confidence", 0),
                "ocr_confidence": ocr_confidence,
                "flags": sanity_result.get("flags", []),
                "warnings": sanity_result.get("warning", ""),
                "ocr_preprocessing": ocr_metadata.get("preprocessing_steps", [])
            }
        }
        
        transaction_id = await _save_transaction(db, tx_payload)
        
        # Step 6: Build result
        result = {
            "transaction_id": transaction_id,
            "llm_response_id": llm_response_id,
            "ocr_text_id": ocr_text_id,
            "receipt_id": receipt_id,
            "status": tx_status,
            "needs_review": needs_review,
            "amount": parsed_output["amount"],
            "category": sanity_result["normalized_category"],
            "ocr_confidence": ocr_confidence,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(
            f"OCR transaction saved successfully: "
            f"tx_id={transaction_id}, receipt_id={receipt_id}, "
            f"amount={parsed_output['amount']}, status={tx_status}, "
            f"ocr_confidence={ocr_confidence:.1f}%"
        )
        
        return result
        
    except DatabaseSaveError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving transaction from OCR: {e}", exc_info=True)
        raise TransactionServiceError(f"Failed to save OCR transaction: {e}") from e

# Additional Helper Functions (Bonus)

async def get_user_transactions(
    user_id: int,
    limit: int = 10,
    intent: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Optional[Any] = None
) -> list:
    """
    Get user transactions dengan filtering (bonus feature)
    
    Args:
        user_id: User ID
        limit: Maximum records
        intent: Filter by 'masuk' or 'keluar'
        start_date: Filter dari tanggal
        end_date: Filter sampai tanggal
        db: Prisma client
    
    Returns:
        List of transaction records
    """
    if db is None:
        logger.warning("No DB client - cannot fetch transactions")
        return []
    
    try:
        where_clause = {"userId": user_id}
        
        if intent:
            where_clause["intent"] = intent
        
        if start_date or end_date:
            where_clause["txDate"] = {}
            if start_date:
                where_clause["txDate"]["gte"] = start_date
            if end_date:
                where_clause["txDate"]["lte"] = end_date
        
        transactions = await db.transaction.find_many(
            where=where_clause,
            order_by={"txDate": "desc"},
            take=limit
        )
        
        return transactions
        
    except Exception as e:
        logger.error(f"Failed to fetch user transactions: {e}", exc_info=True)
        raise TransactionServiceError(f"Failed to fetch transactions: {e}") from e

async def update_transaction_status(
    transaction_id: int,
    new_status: str,
    updated_by: int,
    db: Optional[Any] = None
) -> bool:
    """
    Update transaction status (untuk review process)
    
    Args:
        transaction_id: Transaction ID
        new_status: 'confirmed', 'rejected', 'pending_review'
        updated_by: User ID yang melakukan update
        db: Prisma client
    
    Returns:
        True jika berhasil
    """
    if db is None:
        logger.warning("No DB client - cannot update status")
        return False
    
    try:
        await db.transaction.update(
            where={"id": transaction_id},
            data={
                "status": new_status,
                "updatedAt": datetime.now(),
                "extra": json.dumps({
                    "reviewed_by": updated_by,
                    "reviewed_at": datetime.now().isoformat()
                })
            }
        )
        
        logger.info(
            f"Transaction {transaction_id} status updated to '{new_status}' "
            f"by user {updated_by}"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to update transaction status: {e}", exc_info=True)
        raise TransactionServiceError(f"Failed to update status: {e}") from e