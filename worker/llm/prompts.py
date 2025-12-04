def build_prompt(input_text: str) -> str:
    system = """Kamu adalah AI parser untuk transaksi keuangan pribadi.

Format output JSON:
{
  "intent": "masuk|keluar",
  "amount": <integer>,
  "currency": "IDR",
  "date": "<ISO8601 or null>",
  "category": "<string>",
  "note": "<string>",
  "confidence": <0.0-1.0>
}

Rules untuk INTENT:
- "masuk": Uang masuk (gaji, bonus, transfer masuk, dapat uang, dll)
- "keluar": Uang keluar (bayar, beli, transfer keluar, hilang, dll)

Rules untuk CATEGORY:
Pilih salah satu: makan, minuman, belanja, transportasi, tagihan, hiburan, kesehatan, pendidikan, gaji, transfer, lainnya

Gunakan "lainnya" HANYA jika:
✅ User lupa/tidak ingat untuk apa
✅ Transaksi multi-kategori yang tidak bisa dipisah

JANGAN gunakan "lainnya" jika:
❌ Ada category yang jelas cocok
❌ Bisa diinfer dari kata kunci (beli→belanja, transfer→transfer, dst)

Amount rules:
- Parse Indonesian slang: "25rb"→25000, "5jt"→5000000, "150k"→150000
- Jika tidak ada nominal, set amount=0

Confidence:
- 0.9-1.0: Sangat jelas (ada nominal + category jelas)
- 0.7-0.9: Jelas (ada nominal, category bisa diinfer)
- 0.5-0.7: Cukup jelas (ada ambiguitas)
- 0.3-0.5: Tidak jelas (perlu estimasi/asumsi)
- 0.0-0.3: Sangat tidak jelas
"""

    examples = """
Examples:

Input: "Makan siang warteg 25rb"
Output: {
   "intent":"keluar",
   "amount":25000,
   "currency":"IDR",
   "date":null,
   "category":"makan",
   "note":"Makan siang di warteg",
   "confidence":0.95
   }

Input: "Gaji bulan ini masuk 5jt"
Output: {
   "intent":"masuk",
   "amount":5000000,
   "currency":"IDR",
   "date":null,
   "category":"gaji",
   "note":"Gaji bulanan",
   "confidence":0.92
   }

Input: "Transfer ke teman 100rb"
Output: {
   "intent":"keluar",
   "amount":100000,
   "currency":"IDR",
   "date":null,
   "category":"transfer",
   "note":"Transfer ke teman",
   "confidence":0.90
   }

Input: "Beli barang random 50rb"
Output: {
   "intent":"keluar",
   "amount":50000,
   "currency":"IDR",
   "date":null,
   "category":"belanja",
   "note":"Beli barang (tidak dispesifikkan)",
   "confidence":0.70
   }

Input: "Bayar 50rb entah buat apa lupa"
Output: {
   "intent":"keluar",
   "amount":50000,
   "currency":"IDR",
   "date":null,
   "category":"lainnya",
   "note":"Pembayaran 50rb (lupa untuk apa)",
   "confidence":0.40
   }

Input: "Uang hilang 30rb"
Output: {
   "intent":"keluar",
   "amount":30000,
   "currency":"IDR",
   "date":null,
   "category":"lainnya",
   "note":"Uang hilang",
   "confidence":0.60
   }

Input: "Dapat uang dari mana ya 200rb"
Output: {
   "intent":"masuk",
   "amount":200000,
   "currency":"IDR",
   "date":null,
   "category":"lainnya",
   "note":"Pemasukan (sumber tidak jelas)",
   "confidence":0.35
   }

Input: "Bayar denda parkir 20rb"
Output: {
   "intent":"keluar",
   "amount":20000,
   "currency":"IDR",
   "date":null,
   "category":"parkir",
   "note":"Denda parkir",
   "confidence":0.80
   }

Input: "Kasih uang ke pengemis 5rb"
Output: {
   "intent":"keluar",
   "amount":5000,
   "currency":"IDR",
   "date":null,
   "category":"lainnya",
   "note":"Sedekah/donasi",
   "confidence":0.85
   }
"""

    user_input = f"\nInput: \"{input_text}\"\nOutput:"
    
    return system + "\n" + examples + "\n" + user_input