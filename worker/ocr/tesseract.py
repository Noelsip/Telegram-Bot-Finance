"""
================================================================================
FILE: worker/ocr/tesseract.py
DESKRIPSI: Tesseract OCR Wrapper
ASSIGNEE: @ML/Vision
PRIORITY: HIGH
SPRINT: 2
================================================================================

DEPENDENCIES:
- pytesseract
- Tesseract OCR (system package)

INSTALL TESSERACT:
- Ubuntu/Debian: apt-get install tesseract-ocr tesseract-ocr-ind
- Windows: Download installer dari https://github.com/UB-Mannheim/tesseract/wiki
- MacOS: brew install tesseract

INSTALL PYTHON PACKAGE:
pip install pytesseract

BAHASA YANG DIBUTUHKAN:
- eng (English) - default
- ind (Indonesian) - untuk struk Indonesia

TODO [OCR-001]: Setup Tesseract Path
Untuk Windows, perlu set path ke tesseract.exe:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

Untuk Linux/Docker, biasanya sudah di PATH.

TODO [OCR-002]: extract_text(image_path, lang="ind+eng") -> dict
Fungsi utama untuk extract text dari image.

Parameter:
- image_path: str - path ke preprocessed image
- lang: str - bahasa Tesseract (default: "ind+eng" untuk Indonesia + English)

Return:
{
    "raw_text": str,        # Full extracted text
    "confidence": float,    # Average confidence (0.0 - 1.0)
    "word_count": int,      # Jumlah kata terdeteksi
    "meta": {
        "lang": str,
        "processing_time_ms": int
    }
}

Langkah:
1. Load image dengan PIL.Image.open(image_path)
2. Configure Tesseract:
   - --oem 3 (LSTM neural net)
   - --psm 6 (assume uniform block of text)
3. Extract text: pytesseract.image_to_string(img, lang=lang, config=config)
4. Get detailed data: pytesseract.image_to_data(..., output_type=pytesseract.Output.DICT)
5. Calculate average confidence dari data['conf'] (filter nilai > 0)
6. Return hasil

TODO [OCR-003]: extract_text_with_boxes(image_path) -> dict
Extract text dengan koordinat bounding box.
Berguna jika ingin highlight area di image.

Return tambahan:
{
    "boxes": [
        {"text": "TOTAL", "x": 10, "y": 100, "w": 50, "h": 20, "conf": 95},
        ...
    ]
}

TODO [OCR-004]: PSM (Page Segmentation Mode) Options
Tesseract PSM options yang relevan:
- 3: Fully automatic page segmentation (default)
- 4: Assume single column of text
- 6: Assume uniform block of text (RECOMMENDED untuk struk)
- 11: Sparse text, find as much text as possible
- 13: Raw line, treat image as single text line

Untuk struk, PSM 6 biasanya terbaik.

CATATAN:
- OCR quality sangat bergantung pada preprocessing
- Thermal receipt (struk kasir) biasanya low contrast, perlu threshold yang baik
- Test dengan sample struk real dari berbagai toko
================================================================================
"""
