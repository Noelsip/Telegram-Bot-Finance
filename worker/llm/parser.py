import json
import re
from decimal import Decimal, InvalidOperation


class ParserError(Exception):
    pass


def _extract_json_block(text: str) -> str:
    """
    Mengambil JSON object pertama dari teks LLM secara aman.
    Tidak greedy, kebal terhadap teks tambahan.
    """
    if not isinstance(text, str):
        raise ParserError(f"Expected string, got {type(text)}")

    # Ambil JSON pertama yang seimbang {}
    stack = []
    start = None

    for i, ch in enumerate(text):
        if ch == "{":
            if start is None:
                start = i
            stack.append(ch)
        elif ch == "}":
            if stack:
                stack.pop()
                if not stack and start is not None:
                    return text[start:i + 1]

    raise ParserError("JSON object tidak ditemukan dalam output LLM")


def _normalize_intent(value: str) -> str:
    if not value:
        raise ParserError("Intent kosong")

    v = value.lower()

    if v in ("income", "pemasukan", "masuk"):
        return "income"
    if v in ("expense", "pengeluaran", "keluar"):
        return "expense"

    raise ParserError(f"Intent tidak dikenali: {value}")


def _parse_amount(value) -> Decimal:
    try:
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))

        if isinstance(value, str):
            v = value.lower().replace(" ", "")
            v = v.replace("jt", "000000")
            v = v.replace("juta", "000000")
            v = v.replace("rb", "000")
            return Decimal(v)

        raise ParserError(f"Format amount tidak valid: {value}")

    except InvalidOperation:
        raise ParserError(f"Gagal parse amount: {value}")


def parse_llm_response(llm_text: str) -> dict:
    """
    Mengubah teks LLM menjadi dict transaksi yang tervalidasi dan ternormalisasi.
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

        intent = _normalize_intent(data["intent"])
        amount = _parse_amount(data["amount"])

        try:
            confidence = float(data["confidence"])
        except (TypeError, ValueError):
            raise ParserError(f"Confidence tidak valid: {data['confidence']}")

        return {
            "intent": intent,
            "amount": amount,
            "currency": str(data["currency"]).upper(),
            "date": data["date"],
            "category": str(data["category"]).lower(),
            "note": str(data["note"]),
            "confidence": confidence,
            "raw_output": llm_text
        }

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise ParserError(
            f"Gagal parse LLM response: {e}\nRAW:\n{llm_text}"
        ) from e
