import json, re
from datetime import datetime

def extract_json_from_text(text: str) -> str:
    m = re.search(r'\{.*\}', text, re.S)
    if not m: raise ValueError("No JSON found")
    return m.group(0)

def validate_parsed_output(p: dict) -> dict:
    intent = p.get("intent") if p.get("intent") in {"masuk","keluar","lainnya"} else "lainnya"
    amount = int(p.get("amount") or 0)
    conf = float(p.get("confidence") or 0.0)
    date = p.get("date")
    if date:
        try: datetime.fromisoformat(date)
        except: date = None
    category = p.get("category") or "lainnya"
    note = p.get("note") or ""
    return {
        "intent": intent, "amount": max(0, amount), "currency": "IDR",
        "date": date, "category": category, "note": note,
        "confidence": max(0.0, min(1.0, conf)), "parse_success": True,
        "raw_output": p
    }

def parse_llm_response(llm_response: dict) -> dict:
    try:
        raw = llm_response.get("text","")
        obj = json.loads(extract_json_from_text(raw))
        return validate_parsed_output(obj)
    except Exception as e:
        return {
            "intent":"lainnya","amount":0,"currency":"IDR","date":None,
            "category":"lainnya","note":"Gagal parse response LLM",
            "confidence":0.0,"parse_success":False,"error":str(e),
            "raw_output": llm_response.get("text","")
        }