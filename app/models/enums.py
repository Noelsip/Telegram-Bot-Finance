"""
================================================================================
FILE: app/models/enums.py
DESKRIPSI: Enum definitions (alternatif jika ingin pisah dari schemas)
ASSIGNEE: @Backend
PRIORITY: LOW
SPRINT: 1
================================================================================
"""

from enum import Enum


class IntentType(str, Enum):
    MASUK = "masuk"
    KELUAR = "keluar"
    LAINNYA = "lainnya"


class InputSource(str, Enum):
    TEXT = "text"
    OCR = "ocr"


class TransactionStatus(str, Enum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    REJECTED = "rejected"


class MessageSource(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
