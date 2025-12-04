"""
================================================================================
FILE: worker/services/transaction_service.py
DESKRIPSI: Service untuk menyimpan transaksi dan LLM response
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 2
================================================================================

TODO [TRX-001]: save_llm_response(data) -> LlmResponse
Simpan LLM response ke database.

Parameter (data dict):
- user_id: BigInt
- input_source: "text" | "ocr"
- input_text: str
- prompt_used: str
- llm_output: dict (JSON)
- llm_meta: dict (model name, tokens, etc)

Langkah:
1. prisma.llmresponse.create({
     "userId": user_id,
     "inputSource": input_source,
     "inputText": input_text,
     "promptUsed": prompt_used,
     "llmOutput": llm_output,
     "llmMeta": llm_meta
   })
2. Return created record

TODO [TRX-002]: save_transaction(data) -> Transaction
Simpan transaksi ke database.

Parameter (data dict):
- user_id: BigInt
- llm_response_id: int (FK ke llm_responses)
- receipt_id: int | None (FK ke receipts, jika dari foto)
- intent: str
- amount: int
- currency: str = "IDR"
- tx_date: datetime | None
- category: str
- note: str
- status: str = "confirmed"
- needs_review: bool
- extra: dict | None (sanity check results, flags, etc)

Langkah:
1. prisma.transaction.create(data)
2. Return created record

TODO [TRX-003]: save_ocr_text(receipt_id, ocr_raw, ocr_meta) -> OcrText
Simpan hasil OCR ke database.

Parameter:
- receipt_id: int (FK ke receipts)
- ocr_raw: str (extracted text)
- ocr_meta: dict (confidence, word_count, etc)

Langkah:
1. prisma.ocrtext.create({...})
2. Return created record

TODO [TRX-004]: save_complete_transaction(input_data, llm_result, sanity_result) -> Transaction
High-level function yang save semua sekaligus.

Langkah:
1. Save LLM response -> get llm_response_id
2. Save transaction dengan llm_response_id
3. Return transaction

Parameter:
- input_data: {user_id, input_source, input_text, prompt_used, receipt_id}
- llm_result: {text, model, usage, parsed_output}
- sanity_result: {needs_review, flags, normalized_date, etc}

TODO [TRX-005]: get_transactions_needing_review(user_id=None, limit=50) -> List[Transaction]
Fetch transaksi yang perlu review.

Query:
- WHERE needs_review = True
- Optional filter by user_id
- ORDER BY created_at DESC
- LIMIT limit

TODO [TRX-006]: approve_transaction(transaction_id) -> Transaction
Approve transaksi yang sudah direview.

Update:
- needs_review = False
- extra.reviewed_at = now()
- extra.reviewed_by = "admin" (atau user_id reviewer)

TODO [TRX-007]: reject_transaction(transaction_id, reason) -> Transaction
Reject/delete transaksi yang salah.

Opsi:
- Soft delete: set status = "rejected"
- Hard delete: prisma.transaction.delete()

CATATAN:
- Semua fungsi async
- Wrap dalam try-except untuk error handling
- Return None atau raise exception jika gagal
================================================================================
"""
