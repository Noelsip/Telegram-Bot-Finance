"""
================================================================================
FILE: app/utils/helpers.py
DESKRIPSI: Utility functions
ASSIGNEE: @Backend
PRIORITY: LOW
SPRINT: 1
================================================================================

TODO [UTIL-001]: generate_unique_filename(extension) -> str
Generate filename unik dengan format: {timestamp}_{uuid}.{ext}

TODO [UTIL-002]: parse_phone_number(raw_phone) -> str
Normalisasi nomor telepon (hilangkan +, spasi, dll)
Contoh: "+62 812-3456-789" -> "6281234567890"

TODO [UTIL-003]: format_currency(amount, currency="IDR") -> str
Format angka ke string currency.
Contoh: 50000 -> "Rp50.000"

TODO [UTIL-004]: parse_date_string(date_str) -> datetime | None
Parse berbagai format tanggal ke datetime.
Handle: "2024-12-01", "01/12/2024", "1 Des 2024", etc.

TODO [UTIL-005]: sanitize_text(text) -> str
Bersihkan text dari karakter aneh, trim whitespace, etc.
================================================================================
"""
import uuid
import time
import re
from datetime import datetime

def generate_unique_filename(extension: str) -> str:
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex
    return f"{timestamp}_{unique_id}.{extension}"

def parse_phone_number(raw_phone: str) -> str:
    if not raw_phone:
        return ""
    return re.sub(r'[^\d]', '', raw_phone)

def format_currency(amount: float, currency: str = "IDR") -> str:
    if currency == "IDR":
        return f"Rp{amount:,.0f}".replace(",", ".")
    return str(amount)

def parse_date_string(date_str: str):
    if not date_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()