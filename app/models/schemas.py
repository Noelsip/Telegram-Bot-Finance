"""
================================================================================
FILE: app/models/schemas.py
DESKRIPSI: Pydantic Schemas untuk validasi data
ASSIGNEE: @Backend
PRIORITY: MEDIUM
SPRINT: 1
================================================================================

TODO [SCHEMA-001]: IntentType Enum
- MASUK = "masuk"
- KELUAR = "keluar"  
- LAINNYA = "lainnya"

TODO [SCHEMA-002]: InputSource Enum
- TEXT = "text"
- OCR = "ocr"

TODO [SCHEMA-003]: TransactionStatus Enum
- CONFIRMED = "confirmed"
- PENDING = "pending"
- REJECTED = "rejected"

TODO [SCHEMA-004]: LLMOutputSchema (Pydantic BaseModel)
Schema untuk validasi output dari LLM.

Fields:
- intent: IntentType
- amount: int (harus > 0)
- currency: str = "IDR"
- date: Optional[str] (ISO format YYYY-MM-DD atau null)
- category: str
- note: str
- confidence: float (0.0 - 1.0)

Validators:
- amount harus positif
- confidence harus antara 0 dan 1
- date harus valid ISO format jika ada

TODO [SCHEMA-005]: TransactionCreateSchema
Schema untuk create transaction.

Fields:
- user_id: int
- intent: IntentType
- amount: int
- currency: str = "IDR"
- tx_date: Optional[datetime]
- category: str
- note: Optional[str]
- needs_review: bool = False
- llm_response_id: Optional[int]
- receipt_id: Optional[int]
- extra: Optional[dict]

TODO [SCHEMA-006]: TransactionResponseSchema
Schema untuk response API.

Fields:
- id: int
- All fields from create + created_at

TODO [SCHEMA-007]: WebhookPayloadSchema
Schema untuk incoming webhook (opsional, untuk validasi).

CATATAN:
- Gunakan Pydantic v2 syntax
- Semua schemas inherit dari BaseModel
================================================================================
"""
