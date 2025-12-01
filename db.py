import mysql.connector
from mysql.connector import Error
import config

import pandas as pd
from datetime import datetime, timedelta
import os

# Koneksi ke database
def create_connection():
    try:
        return mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset='utf8'
        )
    except Error as e:
        print(f"Gagal membuat koneksi: {e}")
        return None

# Inisialisasi database dan memastikan tabel sudah dibuat dengan benar
def initialize_db():
    connection = create_connection()
    if connection and connection.is_connected():
        try:
            cursor = connection.cursor()

            # Membuat tabel transaksi0 jika belum ada
            cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS transaksi0 (
                    id INT AUTO_INCREMENT PRIMARY KEY, 
                    user_id BIGINT NOT NULL, 
                    jumlah INT NOT NULL, 
                    kategori VARCHAR(255) NOT NULL, 
                    jenis ENUM('masuk', 'keluar') NOT NULL, 
                    catatan TEXT, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Membuat tabel users0 jika belum ada
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users0 (
                    id BIGINT PRIMARY KEY
                )
            ''')

            # Tambahkan kolom role ke tabel users0 jika belum ada
            try:
                cursor.execute("ALTER TABLE users0 ADD COLUMN role ENUM('Pengguna Biasa', 'Pedagang') DEFAULT 'Pengguna Biasa'")
                print("[INFO] Kolom 'role' ditambahkan ke tabel users0.")
            except Error as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    print("[INFO] Kolom 'role' sudah ada di tabel users0.")
                else:
                    print(f"[WARNING] Gagal menambahkan kolom 'role': {e}")

            # Perbaiki ENUM jika kolom 'jenis' salah (opsional, jika error terjadi sebelumnya)
            try:
                cursor.execute("ALTER TABLE transaksi0 MODIFY COLUMN jenis ENUM('masuk', 'keluar') NOT NULL")
                print("[INFO] Kolom 'jenis' diformat ulang dengan benar.")
            except Error as e:
                print(f"[WARNING] Gagal memodifikasi kolom 'jenis': {e}")

            connection.commit()
            print("Database berhasil diinisialisasi.")
        except Error as e:
            print(f"Gagal menginisialisasi database: {e}")
        finally:
            cursor.close()
            connection.close()

# Fungsi untuk menjalankan query
def execute_query(query, params=(), fetch=False):
    connection = create_connection()
    result = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
            cursor.close()
        except Error as e:
            print(f"Error: {e}")
        finally:
            connection.close()
    return result

# Dapatkan atau buat role user
def get_or_create_user_role(user_id):
    user = execute_query("SELECT * FROM users0 WHERE id = %s", (user_id,), fetch=True)
    if not user:
        execute_query("INSERT INTO users0 (id, role) VALUES (%s, 'Pengguna Biasa')", (user_id,))
        return {'id': user_id, 'role': 'Pengguna Biasa'}
    return user[0]


# Set role user
def set_user_role(user_id, role):
    execute_query(''' 
        INSERT INTO users0 (id, role) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE role = VALUES(role)
    ''', (user_id, role))

# Tambah transaksi
def insert_transaction(user_id, jumlah, kategori, jenis, catatan):
    execute_query('''
        INSERT INTO transaksi0 (user_id, jumlah, kategori, jenis, catatan)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, jumlah, kategori, jenis, catatan))

# Ringkasan transaksi
def get_summary_by_user(user_id):
    result = execute_query('''
        SELECT 
            SUM(CASE WHEN jenis = 'masuk' THEN jumlah ELSE 0 END) AS total_masuk,
            SUM(CASE WHEN jenis = 'keluar' THEN jumlah ELSE 0 END) AS total_keluar
        FROM transaksi0
        WHERE user_id = %s
    ''', (user_id,), fetch=True)
    
    total_masuk = result[0] or {'total_masuk': 0}
    total_keluar = result[0] or {'total_keluar': 0}
    return {
        'masuk': total_masuk['total_masuk'],
        'keluar': total_keluar['total_keluar'],
        'saldo': total_masuk['total_masuk'] - total_keluar['total_keluar']
    }

# Ambil semua transaksi user
def get_all_transactions_by_user(user_id):
    return execute_query('''
        SELECT * FROM transaksi0
        WHERE user_id = %s
        ORDER BY created_at DESC
    ''', (user_id,), fetch=True)

# Transaksi hari ini
def get_today_transactions_by_user(user_id):
    return execute_query('''
        SELECT * FROM transaksi0
        WHERE user_id = %s AND DATE(created_at) = CURDATE()
        ORDER BY created_at DESC
    ''', (user_id,), fetch=True)

# Transaksi berdasarkan kategori
def get_transactions_by_category(user_id, category):
    return execute_query('''
        SELECT * FROM transaksi0
        WHERE user_id = %s AND kategori = %s
        ORDER BY created_at DESC
    ''', (user_id, category), fetch=True)

# Transaksi berdasarkan rentang tanggal
def get_transaction_by_date(user_id, start_date, end_date):
    return execute_query('''
        SELECT * FROM transaksi0
        WHERE user_id = %s AND DATE(created_at) BETWEEN %s AND %s
        ORDER BY created_at DESC
    ''', (user_id, start_date, end_date), fetch=True)

def generate_excel_report(user_id, mode):
    # Tentukan rentang tanggal berdasarkan mode
    today = datetime.today()
    if mode == 'mingguan':
        start_date = today - timedelta(days=7)
    elif mode == 'bulanan':
        start_date = today.replace(day=1)
    elif mode == 'tahunan':
        start_date = today.replace(month=1, day=1)
    else:
        raise ValueError("Mode tidak valid. Gunakan 'mingguan', 'bulanan', atau 'tahunan'.")

    end_date = today

    transactions = get_transaction_by_date(user_id, start_date.date(), end_date.date())

    if not transactions:
        raise ValueError("Tidak ada transaksi ditemukan dalam periode ini.")

    # Buat DataFrame dari hasil transaksi
    df = pd.DataFrame(transactions)
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d-%m-%Y %H:%M')

    # Ubah nama kolom agar lebih jelas di Excel
    df = df.rename(columns={
        'jumlah': 'Jumlah (Rp)',
        'kategori': 'Kategori',
        'jenis': 'Jenis',
        'catatan': 'Catatan',
        'created_at': 'Waktu'
    })
    df = df[['Waktu', 'Jenis', 'Kategori', 'Jumlah (Rp)', 'Catatan']]

    # Simpan sebagai file Excel
    filename = f"laporan_{user_id}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    folder = "exports"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    df.to_excel(file_path, index=False)

    return file_path

# Hapus transaksi hari ini
def delete_daily_transactions(user_id):
    execute_query('''
        DELETE FROM transaksi0
        WHERE user_id = %s AND DATE(created_at) = CURDATE()
    ''', (user_id,))
    print(f"[INFO] Transaksi hari ini untuk user_id {user_id} telah dihapus.")
    return True

# Hapus transaksi mingguan
def delete_weekly_transactions(user_id):
    execute_query('''
        DELETE FROM transaksi0
        WHERE user_id = %s AND DATE(created_at) >= CURDATE() - INTERVAL 7 DAY
    ''', (user_id,))
    
# hapus semua transaksi
def delete_all_transactions(user_id):
    execute_query('''
        DELETE FROM transaksi0
        WHERE user_id = %s
    ''', (user_id,))
    print(f"[INFO] Semua transaksi untuk user_id {user_id} telah dihapus.")
    return True