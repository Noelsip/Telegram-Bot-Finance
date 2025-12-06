"""
================================================================================
FILE: worker/services/sanity_checks.py
DESKRIPSI: Sanity Checks untuk validasi hasil LLM
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 2
================================================================================

TODO [SANITY-001]: run_sanity_checks(parsed_output) -> dict
Fungsi utama untuk menjalankan semua sanity checks.

Parameter:
- parsed_output: dict hasil dari llm.parser.parse_llm_response()

Return:
{
    "needs_review": bool,           # True jika ada flag yang trigger
    "flags": [str],                 # List of triggered flags
    "adjusted_confidence": float,   # Confidence setelah adjustment
    "warnings": [str],              # Warning messages
    "normalized_date": str | None   # Tanggal yang sudah dinormalisasi
}

TODO [SANITY-002]: check_amount_validity(amount) -> dict
Validasi amount.

Rules:
- amount <= 0: INVALID, flag "invalid_amount"
- amount > 1_000_000_000 (1 miliar): flag "unusually_high_amount"
- amount < 1000: flag "unusually_low_amount" (warning only)

Return: {"valid": bool, "flag": str | None, "warning": str | None}

TODO [SANITY-003]: check_confidence_threshold(confidence) -> dict
Check confidence level.

Rules:
- confidence < 0.6: needs_review = True, flag "low_confidence"
- confidence < 0.4: tambah flag "very_low_confidence"

Return: {"needs_review": bool, "flag": str | None}

TODO [SANITY-004]: normalize_date(date_str) -> str | None
Normalisasi tanggal ke ISO format.

Input bisa berupa:
- "2024-12-01" -> "2024-12-01"
- "01/12/2024" -> "2024-12-01"
- "1 Des 2024" -> "2024-12-01"
- None atau invalid -> None

Gunakan dateutil.parser atau manual parsing.

Jika tanggal di masa depan > 7 hari: flag "future_date"
Jika tanggal terlalu lampau > 1 tahun: flag "old_date"

TODO [SANITY-005]: check_category_validity(category) -> dict
Validasi kategori.

Rules:
- Jika category kosong atau "lainnya": warning "uncategorized"
- Normalize category ke lowercase
- Map typos ke kategori yang benar (opsional)

VALID_CATEGORIES = [
    "makan", "minuman", "belanja", "transportasi", "tagihan",
    "hiburan", "kesehatan", "pendidikan", "gaji", "transfer", "lainnya"
]

TODO [SANITY-006]: check_intent_amount_match(intent, amount) -> dict
Cross-check intent dengan amount.

Rules:
- intent = "masuk" dan amount sangat kecil (<10000): warning
- intent = "keluar" dan amount sangat besar (>10jt): warning untuk personal

TODO [SANITY-007]: aggregate_checks(check_results) -> dict
Aggregate semua hasil check ke final result.

Logic:
- needs_review = True jika ANY flag yang critical
- adjusted_confidence = original_confidence * penalty_factor
- Collect semua flags dan warnings

CATATAN:
- Sanity checks adalah safety net
- Better to flag false positives than miss issues
- User bisa review dan approve flagged transactions
================================================================================
"""
