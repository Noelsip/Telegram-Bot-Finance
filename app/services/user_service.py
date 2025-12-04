"""Service untuk operasi User."""

import logging
from typing import Optional

from prisma import Prisma
from prisma.models import User

_logger = logging.getLogger(__name__)


async def get_or_create_user(
    prisma: Prisma,
    user_id: int,
    username: Optional[str] = None,
    display_name: Optional[str] = None,
    source: str = "telegram",
) -> User:
    """Fungsi untuk mendapatkan atau membuat user baru."""
    _logger.debug(f"Getting or creating user: {user_id} from {source}")
    
    try:
        display_name_final = display_name or username or f"User-{user_id}"
        
        # Pakai upsert supaya atomic, hindari race condition
        user = await prisma.user.upsert(
            where={"id": user_id},
            create={
                "id": user_id,
                "username": username,
                "displayName": display_name_final,
            },
            update={},  # Tidak update apa-apa kalau sudah ada
        )
        
        _logger.info(f"User ready: {user_id} ({display_name_final}) from {source}")
        return user
        
    except Exception as e:
        _logger.error(f"Error getting/creating user: {str(e)}", exc_info=True)
        raise


async def update_user(
    prisma: Prisma,
    user_id: int,
    data: dict,
) -> Optional[User]:
    """Update informasi user."""
    _logger.info(f"Updating user {user_id} with data: {data}")
    
    try:
        # Cek dulu apakah user ada
        existing_user = await prisma.user.find_unique(where={"id": user_id})
        
        if not existing_user:
            _logger.warning(f"User not found: {user_id}")
            return None
        
        # Update user
        user = await prisma.user.update(
            where={"id": user_id},
            data=data,
        )
        
        _logger.info(f"User updated: {user_id}")
        return user
        
    except Exception as e:
        _logger.error(f"Error updating user: {str(e)}", exc_info=True)
        raise


async def get_user_by_id(
    prisma: Prisma,
    user_id: int,
    include_receipts: bool = False,
    include_transactions: bool = False,
) -> Optional[User]:
    """Fetch user by ID."""
    _logger.debug(f"Fetching user: {user_id}")
    
    try:
        user = await prisma.user.find_unique(
            where={"id": user_id},
            include={
                "receipts": include_receipts,
                "transactions": include_transactions,
            },
        )
        
        if user:
            _logger.debug(f"User found: {user_id}")
        else:
            _logger.warning(f"User not found: {user_id}")
            
        return user
        
    except Exception as e:
        _logger.error(f"Error fetching user: {str(e)}", exc_info=True)
        raise


async def user_exists(prisma: Prisma, user_id: int) -> bool:
    """Check if user exists."""
    user = await get_user_by_id(prisma, user_id)
    return user is not None


async def get_user_stats(prisma: Prisma, user_id: int) -> dict:
    """Ambil statistik user (jumlah receipts, transactions, etc)."""
    try:
        # Hitung jumlah receipts
        receipt_count = await prisma.receipt.count(where={"userId": user_id})
        
        # Hitung jumlah transactions
        transaction_count = await prisma.transaction.count(where={"userId": user_id})
        
        return {
            "user_id": user_id,
            "receipt_count": receipt_count,
            "transaction_count": transaction_count,
        }
        
    except Exception as e:
        _logger.error(f"Error getting user stats: {str(e)}", exc_info=True)
        return {
            "user_id": user_id,
            "receipt_count": 0,
            "transaction_count": 0,
        }
