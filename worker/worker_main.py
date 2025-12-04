"""
================================================================================
FILE: worker/worker_main.py
DESKRIPSI: Worker Entry Point - Processing Orchestrator
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 2
================================================================================

CATATAN:
Karena tidak menggunakan Redis queue, worker functions akan dipanggil
langsung dari webhook handlers secara synchronous atau dengan BackgroundTasks.

TODO [WORKER-001]: process_text_message(user_id, text, source) -> Transaction
Fungsi utama untuk memproses pesan teks.

Parameter:
- user_id: BigInt
- text: str (pesan dari user)
- source: str ("telegram" atau "whatsapp")

Alur:
1. Build prompt dengan text menggunakan llm.prompts.build_prompt(text)
2. Call Gemini API: llm.gemini_client.call_gemini(prompt)
3. Parse response: llm.parser.parse_llm_response(response)
4. Run sanity checks: services.sanity_checks.run_checks(parsed)
5. Save LLM response ke database
6. Save transaction ke database dengan status=confirmed
7. Return transaction untuk dikirim ke user

TODO [WORKER-002]: process_image_message(user_id, receipt_id, file_path, source) -> Transaction
Fungsi utama untuk memproses pesan gambar/foto.

Parameter:
- user_id: BigInt
- receipt_id: int (ID dari table receipts)
- file_path: str (path ke file gambar)
- source: str

Alur:
1. Preprocess image: ocr.preprocessor.preprocess_image(file_path)
2. Extract text: ocr.tesseract.extract_text(preprocessed_path)
3. Save OCR result ke database (ocr_texts table)
4. Build prompt dengan OCR text
5. Call Gemini API
6. Parse response
7. Run sanity checks
8. Save LLM response dengan input_source="ocr"
9. Save transaction dengan receipt_id
10. Return transaction

TODO [WORKER-003]: Error Handling Wrapper
Wrap process functions dengan try-except.

Jika error:
- Log error details
- Return None atau raise custom exception
- Caller (webhook) akan handle dan notify user

TODO [WORKER-004]: Background Task Option
Jika processing terlalu lama (>5 detik), gunakan FastAPI BackgroundTasks:

from fastapi import BackgroundTasks

@router.post("/")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # ... parse request ...
    background_tasks.add_task(process_text_message, user_id, text, "telegram")
    return {"status": "processing"}

Tapi ini berarti user tidak langsung dapat response.
Alternatif: kirim "Sedang memproses..." dulu, lalu kirim hasil setelah selesai.
================================================================================
"""
