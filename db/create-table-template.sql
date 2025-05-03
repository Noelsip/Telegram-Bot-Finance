CREATE TABLE transaksi(
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    jenis VARCHAR(20),
    jumlah INT,
    tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    catatan TEXT
);