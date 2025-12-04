from enum import Enum


class IntentType(str, Enum):
    PEMASUKAN   = "pemasukan"
    PENGELUARAN = "pengeluaran"

class InputSource(str, Enum):
    TEXT = "text"
    OCR = "ocr"


class MessageSource(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
