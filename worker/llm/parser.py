import json
import re
from decimal import Decimal

class ParserError(Exception):
    pass


def _extract_json_block(text: str) -> str:
    """
    Mengambil JSON object pertama dari teks LLM
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ParserError("Tidak ditemukan JSON object dalam response LLM")
    return match.group(0)


def parse_llm_response(llm_text: str) -> dict:
    """
    Parse dan validasi response LLM menjadi struktur transaksi
    """
    try:
        json_text = _extract_json_block(llm_text)
        data = json.loads(json_text)

        required_fields = [
            "intent",
            "amount",
            "currency",
            "date",
            "category",
            "note",
            "confidence"
        ]

        for field in required_fields:
            if field not in data:
                raise ParserError(f"Field '{field}' tidak ditemukan")

        return {
            "intent": data["intent"],
            "amount": Decimal(str(data["amount"])),
            "currency": data["currency"],
            "date": data["date"],
            "category": data["category"],
            "note": data["note"],
            "confidence": float(data["confidence"]),
            "raw_output": llm_text
        }

    except (json.JSONDecodeError, ValueError) as e:
        raise ParserError(f"Gagal parse JSON: {e}") from e
