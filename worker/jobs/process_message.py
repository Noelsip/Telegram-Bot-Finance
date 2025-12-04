"""
================================================================================
FILE: worker/jobs/process_message.py
DESKRIPSI: Job handler untuk memproses pesan (alternatif modular dari worker_main)
ASSIGNEE: @Backend
PRIORITY: MEDIUM
SPRINT: 2
================================================================================

TODO [JOB-001]: ProcessMessageJob Class (Opsional)
Jika ingin struktur OOP, buat class:

class ProcessMessageJob:
    def __init__(self, user_id, input_type, data):
        self.user_id = user_id
        self.input_type = input_type  # "text" atau "image"
        self.data = data

    async def execute(self):
        if self.input_type == "text":
            return await self._process_text()
        else:
            return await self._process_image()

    async def _process_text(self):
        # ... implementasi ...
        pass

    async def _process_image(self):
        # ... implementasi ...
        pass

TODO [JOB-002]: Implement helper methods
- _build_and_call_llm(text) -> dict
- _save_results(llm_output, ocr_text=None, receipt_id=None) -> Transaction
- _determine_review_flag(parsed_output, sanity_result) -> bool

CATATAN:
Ini adalah alternatif struktur. Bisa pilih antara:
1. Semua di worker_main.py (simple)
2. Pisah ke class di sini (lebih modular)

Tim bisa pilih mana yang lebih nyaman.
================================================================================
"""
