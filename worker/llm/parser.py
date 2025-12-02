"""
================================================================================
FILE: worker/llm/parser.py
DESKRIPSI: LLM Response Parser
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 2
================================================================================

TODO [PARSER-001]: parse_llm_response(llm_response) -> dict
Parse raw LLM response ke structured dict.

Parameter:
- llm_response: dict dari gemini_client.call_gemini()
  Berisi: {"text": "...", "model": "...", ...}

Return:
{
    "intent": "masuk|keluar|lainnya",
    "amount": int,
    "currency": "IDR",
    "date": "YYYY-MM-DD" | None,
    "category": str,
    "note": str,
    "confidence": float,
    "raw_output": str,      # Original LLM text untuk debugging
    "parse_success": bool   # True jika berhasil parse
}

Langkah:
1. Extract text dari llm_response["text"]
2. Clean text:
   - Hapus markdown code blocks (```json ... ```)
   - Hapus whitespace di awal/akhir
3. Parse JSON dengan json.loads()
4. Validate dengan Pydantic schema (LLMOutputSchema)
5. Return parsed dict

TODO [PARSER-002]: extract_json_from_text(text) -> str
Helper untuk extract JSON dari text yang mungkin mengandung noise.

Cases yang harus di-handle:
1. Pure JSON: {"intent": ...}
2. Markdown code block: ```json\n{...}\n```
3. Markdown tanpa language: ```\n{...}\n```
4. Text sebelum/sesudah JSON: "Here is the result: {...}"

Approach:
- Regex untuk find JSON object: r'\{[^{}]*\}'
- Atau cari index { pertama dan } terakhir

TODO [PARSER-003]: validate_parsed_output(parsed) -> dict
Validasi dan sanitize parsed output.

Checks:
- intent harus salah satu dari: masuk, keluar, lainnya
- amount harus integer >= 0
- confidence harus float 0.0 - 1.0
- date jika ada harus valid ISO format
- category tidak boleh empty

Jika invalid, set default values dan turunkan confidence.

TODO [PARSER-004]: Error Handling
Jika parsing gagal:
- Log error dengan full LLM response
- Return default object dengan:
  {
    "intent": "lainnya",
    "amount": 0,
    "currency": "IDR",
    "date": None,
    "category": "lainnya",
    "note": "Gagal parse response LLM",
    "confidence": 0.0,
    "parse_success": False,
    "error": str(exception)
  }

Jangan raise exception, biarkan flow lanjut tapi flag as needs_review.

CATATAN:
- LLM output bisa inconsistent, parser harus robust
- Log semua parsing errors untuk improvement
- Confidence dari LLM + parse success menentukan needs_review
================================================================================
"""
