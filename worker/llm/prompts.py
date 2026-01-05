def build_prompt(input_text: str, input_source: str = "text") -> str:
    """
    Build prompt for LLM - adaptive based on input source
    
    Args:
        input_text: Input text (user message or OCR result)
        input_source: "text" or "ocr"
    """
    
    if input_source == "ocr":
        return _build_receipt_prompt(input_text)
    else:
        return _build_text_prompt(input_text)


def _build_text_prompt(input_text: str) -> str:
    """Prompt untuk text message (supports multiple transactions)"""
    system = """Kamu adalah AI parser untuk transaksi keuangan pribadi.

Format output JSON untuk MULTIPLE transaksi:
{
  "transactions": [
    {
      "intent": "Pemasukan|Pengeluaran",
      "amount": <integer>,
      "currency": "IDR",
      "date": "<ISO8601 or null>",
      "category": "<string>",
      "note": "<string>",
      "confidence": <0.0-1.0>
    }
  ]
}

PENTING:
- Jika ada MULTIPLE transaksi dalam satu input, pisahkan menjadi array "transactions"
- Jika hanya 1 transaksi, tetap gunakan array dengan 1 element
- Detect kata pemisah: "dan", "kemarin", "tadi", "juga", koma, titik koma

Rules untuk INTENT:
- "Pemasukan": Uang masuk (gaji, bonus, transfer masuk, dapat uang, dll)
- "Pengeluaran": Uang keluar (bayar, beli, transfer keluar, hilang, dll)

Rules untuk CATEGORY:
Pilih salah satu: makan, minuman, belanja, transportasi, tagihan, hiburan, kesehatan, pendidikan, gaji, transfer, lainnya

Amount rules:
- Parse Indonesian slang: "25rb"→25000, "5jt"→5000000, "150k"→150000
- Jika tidak ada nominal, set amount=0

Confidence:
- 0.9-1.0: Sangat jelas
- 0.7-0.9: Jelas
- 0.5-0.7: Cukup jelas
- 0.3-0.5: Tidak jelas
- 0.0-0.3: Sangat tidak jelas
"""

    examples = """
Examples:

Input: "Makan siang warteg 25rb"
Output: {
   "transactions": [
     {
       "intent":"Pengeluaran",
       "amount":25000,
       "currency":"IDR",
       "date":null,
       "category":"makan",
       "note":"Makan siang di warteg",
       "confidence":0.95
     }
   ]
}

Input: "hari ini beli makan 50rb, kemarin beli rokok 20rb, gajian 500rb"
Output: {
   "transactions": [
     {
       "intent":"Pengeluaran",
       "amount":50000,
       "currency":"IDR",
       "date":"today",
       "category":"makan",
       "note":"Beli makan hari ini",
       "confidence":0.90
     },
     {
       "intent":"Pengeluaran",
       "amount":20000,
       "currency":"IDR",
       "date":"yesterday",
       "category":"lainnya",
       "note":"Beli rokok kemarin",
       "confidence":0.88
     },
     {
       "intent":"Pemasukan",
       "amount":500000,
       "currency":"IDR",
       "date":null,
       "category":"gaji",
       "note":"Gajian",
       "confidence":0.92
     }
   ]
}
"""

    user_input = f"\nInput: \"{input_text}\"\nOutput:"
    return system + "\n" + examples + "\n" + user_input


def _build_receipt_prompt(ocr_text: str) -> str:
    """
    Prompt khusus untuk OCR result - SINGLE transaction dari struk
    More robust untuk OCR errors
    """
    system = """Kamu adalah AI parser untuk struk pembayaran.

Input adalah hasil OCR dari foto struk yang mungkin TIDAK SEMPURNA.
OCR bisa mengandung:
- Karakter salah (0→O, 1→I, 5→S)
- Kata terpotong atau typo
- Angka tidak lengkap
- Urutan baris acak

TUGAS KAMU:
1. Identifikasi TOTAL AMOUNT (cari kata: TOTAL, JUMLAH, AMOUNT, BAYAR, GRAND TOTAL)
2. Tentukan merchant/toko (biasanya di bagian atas)
3. Cari tanggal transaksi
4. Kategori berdasarkan jenis toko

Format output JSON (SINGLE transaction untuk struk):
{
  "transactions": [
    {
      "intent": "Pengeluaran",
      "amount": <integer>,
      "currency": "IDR",
      "date": "<YYYY-MM-DD or null>",
      "category": "<string>",
      "note": "<merchant name + detail>",
      "confidence": <0.0-1.0>
    }
  ]
}

CATEGORY detection:
- Indomaret/Alfamart/minimarket → "belanja"
- Warteg/Restoran/Cafe/food → "makan"
- Starbucks/Kopi/drink → "minuman"
- Apotik/Farmasi → "kesehatan"
- PLN/Listrik/Telkom/pulsa → "tagihan"
- Cinema/XXI/bioskop → "hiburan"
- Gojek/Grab/taxi → "transportasi"
- Lainnya → "lainnya"

AMOUNT parsing rules:
- Cari baris dengan kata: TOTAL, JUMLAH, AMOUNT, GRAND TOTAL, BAYAR
- Ambil angka TERBESAR (biasanya total akhir)
- Handle OCR errors: O→0, I/l→1, S→5, B→8
- Format: 25000, 125.000, Rp 125.000

CONFIDENCE scoring:
- 0.8-1.0: Total amount jelas, tanggal ada, merchant identified
- 0.6-0.8: Total amount found, tapi tanggal/merchant tidak jelas
- 0.4-0.6: Amount found tapi banyak noise
- 0.0-0.4: OCR result sangat buruk, amount tidak jelas

NOTE format: "<Merchant Name> - <optional detail>"
Example: "Indomaret - Belanja bulanan", "Warteg Bahari - Makan siang"
"""

    examples = """
Examples:

Input (good OCR):
\"\"\"
INDOMARET
JL. SUDIRMAN NO 123
========================
SUSU ULTRA 250ML    12.500
MIE INDOMIE        2.500
AIR MINERAL         3.000
------------------------
TOTAL              18.000
TUNAI              20.000
KEMBALI             2.000
========================
25/12/2024 14:35
\"\"\"

Output:
{
  "transactions": [{
    "intent": "Pengeluaran",
    "amount": 18000,
    "currency": "IDR",
    "date": "2024-12-25",
    "category": "belanja",
    "note": "Indomaret - Belanja harian",
    "confidence": 0.95
  }]
}

Input (poor OCR with errors):
\"\"\"
WARTEG BAHARl          <-- typo 'I' instead of 'i'
JL GATSU
NASI PUTIH      8OOO   <-- OCR: O→0
AYAM GORENG    15OOO   <-- OCR: O→0
TAHU           3OOO
T0TAL          26OOO   <-- OCR: 0→O
TUNAI          5OOOO
24 DES 2O24            <-- OCR: O→0
\"\"\"

Output:
{
  "transactions": [{
    "intent": "Pengeluaran",
    "amount": 26000,
    "currency": "IDR",
    "date": "2024-12-24",
    "category": "makan",
    "note": "Warteg Bahari - Makan siang",
    "confidence": 0.75
  }]
}

Input (very poor OCR):
\"\"\"
ALP4M4RT         <-- heavy OCR errors
saKuR4 No 99
C0K4            5.5OO
M1E SEd4P       3.2OO
T4HU            2.OOO
JuML4H         1O.7OO
\"\"\"

Output:
{
  "transactions": [{
    "intent": "Pengeluaran",
    "amount": 10700,
    "currency": "IDR",
    "date": null,
    "category": "belanja",
    "note": "Alfamart - Belanja",
    "confidence": 0.65
  }]
}
"""

    user_input = f"\nInput (OCR Result):\n\"\"\"\n{ocr_text}\n\"\"\"\n\nOutput:"
    return system + "\n" + examples + "\n" + user_input