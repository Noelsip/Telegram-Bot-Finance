import re
import spacy

nlp = spacy.load("en_core_web_sm")

# Daftar kata kunci sederhana
kata_pemasukan = ["gaji", "dapat", "masuk", "transfer", "bayaran", "terjual", "jual", "jualan", "transfer", "terima", "pemasukan", "bonus", "komisi", "uang", "cashback"]
kata_pengeluaran = ["makan", "belanja", "bayar", "tagihan", "beli", "pesan", "keluar", "sewa", "hiburan", "transportasi", "angkutan", "mobil", "kesehatan", "obat", "dokter", "pendidikan", "sekolah", "kuliah", "snack", "liburan"]

kategori_kata = {
    "gaji": ["gaji", "upah", "bayaran"],
    "makan": ["makan", "minum", "snack"],
    "belanja": ["belanja", "beli"],
    "tagihan": ["tagihan", "sewa", "bayar"],
    "hiburan": ["hiburan", "nonton", "liburan"],
    "transportasi": ["transportasi", "angkutan", "mobil"],
    "kesehatan": ["kesehatan", "obat", "dokter"],
    "pendidikan": ["pendidikan", "sekolah", "kuliah"],
    "lainnya": []
}

def parse_transaksi(text, role="pengguna biasa"):
    # Menganalisis teks
    text_lower = text.lower()
    
    jumlah = extract_jumlah(text_lower)
    
    jenis = detect_jenis(text_lower, role)
    
    kategori = detect_kategori(text_lower)
    
    return {
        "jumlah": jumlah,
        "jenis": jenis,
        "kategori": kategori,
        "catatan": text
    }

def extract_jumlah(text):
    # Mencari angka dalam teks
    match = re.search(r'(\d+(?:[\.,]\d+)?)(\s*(rb|ribu|k|jt|juta)?)', text)
    if not match:
        return 0
    
    nominal = float(match.group(1).replace('.', '').replace(',', '.'))
    satuan = match.group(3)
    
    if satuan in ['rb', 'ribu', 'k']:
        return int(nominal * 1_000)
    elif satuan in ['jt', 'juta']:
        return int(nominal * 1_000_000)
    else:
        return int(nominal)

def detect_jenis(text, role):
    # Mendeteksi jenis transaksi berdasarkan peran (role)
    for kata in kata_pemasukan:
        if kata in text:
            if role == "pedagang" and "terjual" in text:
                return "masuk"  # Untuk pedagang, transaksi dianggap pemasukan
            return "masuk"  # Untuk pengguna biasa, transaksi masuk
    
    for kata in kata_pengeluaran:
        if kata in text:
            return "keluar"  # Untuk pengguna biasa dan pedagang, transaksi keluar
    
    return "lainnya"

def detect_kategori(text):
    # Mendeteksi kategori transaksi
    for kategori, kata_list in kategori_kata.items():
        for kata in kata_list:
            if kata in text:
                return kategori
    
    # Jika tidak ada kategori yang cocok, kembalikan "lainnya"
    return "lainnya"
