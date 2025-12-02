"""
================================================================================
FILE: worker/services/ocr_service.py
DESKRIPSI: Service untuk OCR operations
ASSIGNEE: @Backend
PRIORITY: MEDIUM
SPRINT: 2
================================================================================

TODO [OCRSVC-001]: process_receipt_image(file_path) -> dict
High-level function untuk proses image ke text.

Langkah:
1. Call preprocessor.preprocess_image(file_path)
2. Call tesseract.extract_text(preprocessed_path)
3. Cleanup temp files (preprocessed image)
4. Return OCR result

Return:
{
    "raw_text": str,
    "confidence": float,
    "meta": dict
}

TODO [OCRSVC-002]: save_ocr_result(receipt_id, ocr_result) -> OcrText
Simpan hasil OCR ke database.

Langkah:
1. Call transaction_service.save_ocr_text(receipt_id, ocr_result["raw_text"], ocr_result["meta"])
2. Return created OcrText

TODO [OCRSVC-003]: get_ocr_by_receipt(receipt_id) -> OcrText | None
Fetch OCR result untuk receipt tertentu.

CATATAN:
- Ini adalah wrapper/orchestrator untuk OCR operations
- Actual OCR logic ada di worker/ocr/
================================================================================
"""
