"""
================================================================================
FILE: app/services/receipt_service.py
DESKRIPSI: Service untuk operasi Receipt (struk/foto)
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 1
================================================================================

TODO [RECEIPT-001]: create_receipt(user_id, file_path, file_name, mime_type, file_size) -> Receipt
Simpan record receipt ke database.

Langkah:
1. prisma.receipt.create({
     "userId": user_id,
     "filePath": file_path,
     "fileName": file_name,
     "mimeType": mime_type,
     "fileSize": file_size
   })
2. Return created receipt dengan ID

TODO [RECEIPT-002]: get_receipt_by_id(receipt_id) -> Receipt
Fetch receipt by ID.

TODO [RECEIPT-003]: get_receipts_by_user(user_id, limit=10) -> List[Receipt]
Fetch receipts milik user tertentu.

TODO [RECEIPT-004]: delete_receipt(receipt_id)
Hapus receipt dari database.
Opsional: hapus juga file fisik dari uploads/

CATATAN:
- Receipt adalah parent dari OcrText (one-to-many)
- Receipt bisa linked ke Transaction (one-to-one optional)
================================================================================
"""
