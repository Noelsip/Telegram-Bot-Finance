import json
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict


class ParserError(Exception):
    pass


def _extract_json_block(text: str) -> str:
    """Extract JSON object dari LLM output"""
    if not isinstance(text, str):
        raise ParserError(f"Expected string, got {type(text)}")

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
    """Normalize intent value"""
    if not value:
        raise ParserError("Intent kosong")

    v = value.lower()

    if v in ("income", "pemasukan", "masuk"):
        return "income"
    if v in ("expense", "pengeluaran", "keluar"):
        return "expense"

    raise ParserError(f"Intent tidak dikenali: {value}")


def _parse_amount(value) -> Decimal:
    """Parse amount dari berbagai format"""
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


def _parse_single_transaction(data: Dict) -> Dict:
    """Parse single transaction object"""
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
        "confidence": confidence
    }


def parse_llm_response(llm_text: str) -> List[Dict]:
    """
    Parse LLM response - supports MULTIPLE transactions
    
    Returns:
        List[Dict]: List of parsed transactions
    """
    try:
        json_text = _extract_json_block(llm_text)
        data = json.loads(json_text)

        # Check if response has "transactions" array
        if "transactions" in data:
            transactions = data["transactions"]
            
            if not isinstance(transactions, list):
                raise ParserError("'transactions' harus berupa array")
            
            if len(transactions) == 0:
                raise ParserError("Array 'transactions' kosong")
            
            # Parse each transaction
            parsed_list = []
            for i, tx in enumerate(transactions):
                try:
                    parsed_tx = _parse_single_transaction(tx)
                    parsed_tx["raw_output"] = llm_text
                    parsed_tx["transaction_index"] = i
                    parsed_list.append(parsed_tx)
                except ParserError as e:
                    raise ParserError(f"Error parsing transaction #{i+1}: {e}")
            
            return parsed_list
        
        else:
            # Fallback: single transaction (old format)
            parsed_tx = _parse_single_transaction(data)
            parsed_tx["raw_output"] = llm_text
            parsed_tx["transaction_index"] = 0
            return [parsed_tx]

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise ParserError(
            f"Gagal parse LLM response: {e}\nRAW:\n{llm_text}"
        ) from e