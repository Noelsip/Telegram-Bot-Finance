"""
================================================================================
FILE: worker/llm/prompts.py
DESKRIPSI: LLM Prompt Templates
ASSIGNEE: @ML/NLP
PRIORITY: HIGH
SPRINT: 2
================================================================================

TODO [PROMPT-001]: SYSTEM_PROMPT Constant
Definisikan system instruction untuk LLM.

Isi harus mencakup:
1. Role: "Kamu adalah asisten keuangan yang mengekstrak informasi transaksi"
2. Task: "Analisis teks dan hasilkan JSON terstruktur"
3. Output format: JSON schema yang diharapkan
4. Rules:
   - intent: masuk (pemasukan), keluar (pengeluaran), lainnya
   - amount: integer dalam rupiah
   - currency: selalu "IDR"
   - date: ISO format YYYY-MM-DD atau null
   - category: kategori transaksi
   - note: catatan singkat
   - confidence: 0.0 - 1.0
5. Conversion rules:
   - "rb", "ribu", "k" = x1000
   - "jt", "juta" = x1000000
6. Constraints:
   - HANYA output JSON, tanpa penjelasan
   - Confidence rendah jika ambigu

TODO [PROMPT-002]: FEW_SHOT_EXAMPLES Constant
Definisikan contoh-contoh untuk few-shot learning.

Minimal 5-10 contoh yang mencakup:
1. Pengeluaran sederhana: "makan siang 25rb"
2. Pemasukan gaji: "gaji masuk 5jt"
3. Tagihan: "bayar listrik 350000"
4. OCR struk minimarket
5. OCR struk restoran
6. Kasus ambigu (confidence rendah)
7. Tanggal eksplisit: "beli buku 50rb tgl 5 desember"
8. Tanpa nominal (harus confidence sangat rendah)

Format setiap contoh:
Input: "..."
Output: {"intent":"...", "amount":..., ...}

TODO [PROMPT-003]: build_prompt(input_text) -> str
Fungsi untuk membangun prompt lengkap.

Struktur:
1. SYSTEM_PROMPT
2. FEW_SHOT_EXAMPLES
3. "Sekarang analisis input berikut:"
4. f'Input: "{input_text}"'
5. "Output:"

Return: complete prompt string

TODO [PROMPT-004]: Kategori yang Didukung
Dokumentasikan kategori yang valid:
- makan: makanan, snack, restoran
- minuman: kopi, teh, minuman
- belanja: grocery, shopping
- transportasi: bensin, parkir, grab, gojek
- tagihan: listrik, air, internet, pulsa
- hiburan: nonton, game, langganan streaming
- kesehatan: obat, dokter, apotek
- pendidikan: buku, kursus, sekolah
- gaji: gaji bulanan, bonus, THR
- transfer: transfer masuk/keluar
- lainnya: tidak terklasifikasi

TODO [PROMPT-005]: Edge Cases dalam Prompt
Tambahkan instruksi untuk edge cases:
- Jika tidak ada nominal: amount=0, confidence<0.3
- Jika bahasa campur (Inggris+Indonesia): tetap parse
- Jika format struk berantakan: extract total saja
- Jika multiple items: jumlahkan atau ambil total

CATATAN:
- Prompt quality sangat mempengaruhi hasil
- Test dengan berbagai variasi input
- Iterate dan improve berdasarkan hasil real
- Dokumentasikan setiap perubahan prompt
================================================================================
"""
