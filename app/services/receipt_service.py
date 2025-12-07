"""Service untuk operasi Receipt (struk/foto)."""

import logging
from pathlib import Path
from typing import List, Optional

from prisma import Prisma
from prisma.models import Receipt

_logger = logging.getLogger(__name__)


async def create_receipt(
    prisma: Prisma,
    user_id: int,
    file_path: str,
    file_name: str,
    mime_type: str,
    file_size: int,
) -> Receipt:
    """Simpan record receipt ke database."""
    _logger.info(f"Creating receipt for user {user_id}: {file_name}")
    
    try:
        receipt = await prisma.receipt.create(
            data={
                "userId": user_id,
                "filePath": file_path,
                "fileName": file_name,
                "mimeType": mime_type,
                "fileSize": file_size,
            }
        )
        
        _logger.info(f"Receipt created with ID: {receipt.id}")
        return receipt
        
    except Exception as e:
        _logger.error(f"Error creating receipt: {str(e)}", exc_info=True)
        raise


async def get_receipt_by_id(
    prisma: Prisma,
    receipt_id: int,
    include_user: bool = False,
    include_ocr: bool = False,
    include_transaction: bool = False,
) -> Optional[Receipt]:
    """Fetch receipt by ID."""
    _logger.debug(f"Fetching receipt ID: {receipt_id}")
    
    try:
        receipt = await prisma.receipt.find_unique(
            where={"id": receipt_id},
            include={
                "user": include_user,
                "ocrTexts": include_ocr,
                "transaction": include_transaction,
            },
        )
        
        if receipt:
            _logger.debug(f"Receipt found: {receipt.id}")
        else:
            _logger.warning(f"Receipt not found: {receipt_id}")
            
        return receipt
        
    except Exception as e:
        _logger.error(f"Error fetching receipt: {str(e)}", exc_info=True)
        raise


async def get_receipts_by_user(
    prisma: Prisma,
    user_id: int,
    limit: int = 10,
    skip: int = 0,
    include_ocr: bool = False,
    include_transaction: bool = False,
) -> List[Receipt]:
    """Fetch receipts milik user tertentu."""
    _logger.debug(f"Fetching receipts for user {user_id} (limit={limit}, skip={skip})")
    
    try:
        receipts = await prisma.receipt.find_many(
            where={"userId": user_id},
            take=limit,
            skip=skip,
            order={"uploadedAt": "desc"},
            include={
                "ocrTexts": include_ocr,
                "transaction": include_transaction,
            },
        )
        
        _logger.info(f"Found {len(receipts)} receipts for user {user_id}")
        return receipts
        
    except Exception as e:
        _logger.error(f"Error fetching receipts: {str(e)}", exc_info=True)
        raise


async def delete_receipt(
    prisma: Prisma,
    receipt_id: int,
    delete_file: bool = True,
) -> dict:
    """Hapus receipt dari database."""
    _logger.info(f"Deleting receipt ID: {receipt_id}")
    
    try:
        # Fetch receipt untuk ambil file path
        receipt = await prisma.receipt.find_unique(where={"id": receipt_id})
        
        if not receipt:
            _logger.warning(f"Receipt not found: {receipt_id}")
            return {
                "success": False,
                "receipt_id": receipt_id,
                "file_deleted": False,
                "message": "Receipt not found",
            }
        
        file_path = receipt.filePath
        file_deleted = False
        
        # Hapus file fisik jika diminta
        if delete_file and file_path:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    file_deleted = True
                    _logger.info(f"File deleted: {file_path}")
                else:
                    _logger.warning(f"File not found: {file_path}")
            except Exception as e:
                _logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        
        # Hapus dari database (cascade akan hapus ocrTexts juga)
        await prisma.receipt.delete(where={"id": receipt_id})
        
        _logger.info(f"Receipt deleted: {receipt_id}")
        
        return {
            "success": True,
            "receipt_id": receipt_id,
            "file_deleted": file_deleted,
            "message": "Receipt deleted successfully",
        }
        
    except Exception as e:
        _logger.error(f"Error deleting receipt: {str(e)}", exc_info=True)
        raise


async def count_receipts_by_user(prisma: Prisma, user_id: int) -> int:
    """Hitung total receipts untuk user."""
    count = await prisma.receipt.count(where={"userId": user_id})
    return count


async def get_latest_receipt(prisma: Prisma, user_id: int) -> Optional[Receipt]:
    """Ambil receipt terbaru untuk user."""
    receipts = await get_receipts_by_user(prisma, user_id, limit=1)
    return receipts[0] if receipts else None
