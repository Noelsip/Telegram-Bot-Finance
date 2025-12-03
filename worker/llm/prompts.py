SYSTEM_PROMPT = """
Posisikan diri anda sebagai asisten Keuangan.
Keluarkan HANYA JSON:
{
    "intent": "masuk" (pemasukan), "keluar" (pengeluaran)
    "amount": integer 
    "currency": "IDR"
    "date": "YYYY-MM-DD" atau null
    "category": kategori transaksi
    "note": catatan singkat
    "confidence": 0.0 - 1.0
}
Konversi: rb/k/ribu=x1000, jt/juta=x1000000, milyar=x1000000000. 
Jika tidak jelas, confidence rendah
"""

FEW_SHOT_EXAMPLES = """
   Input: "makan siang 25 ribu"
   output: {
      "intent": "keluar"
      "amount": 25000
      "currency": "IDR"
      "date": null
      "category": "makan"
      "note": "makan siang"
      "confidence": 0.9
   }

   Input: "gaji masuk 5jt"
   output: {
      "intent": "masuk"
      "amount": 5000000
      "currency": "IDR"
      "date": null
      "category": "gaji"
      "note": "gaji masuk"
      "confidence": 0.9
   }
"""

def build_prompt(input_text):
    return f"{SYSTEM_PROMPT}\n{FEW_SHOT_EXAMPLES}\nSekarang analisis input berikut\nInput: \"{input_text}\"\nOutput: "
    