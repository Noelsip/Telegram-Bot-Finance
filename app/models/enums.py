from enum import Enum

class IntentType(str, Enum):
    PEMASUKAN   = "pemasukan"
    PENGELUARAN = "pengeluaran"

class InputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"

class MessageSource(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
