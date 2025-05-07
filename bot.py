import httpx
import db
import config
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from nlp_parser import parse_transaksi

# daftar perintah tersedia
commands = {
    "/start": "Mulai bot",
    # "/Chat": "Transaksi chat",
    "/help": "Bantuan dan daftar perintah",
    "/saldo": "Cek saldo",
    "/history": "Riwayat transaksi",
    "/history_today": "Riwayat transaksi hari ini",
    "/history_kategori": "Riwayat transaksi berdasarkan kategori",
    "/export_mingguan": "Ekspor data mingguan",
    "/export_bulanan": "Ekspor data bulanan",
    "/export_tahunan": "Ekspor data tahunan"
}

# --- Start Command Handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Pengguna Biasa", "Pedagang"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    try:
        await update.message.reply_text(
        "Selamat datang! Silakan pilih jenis pengguna Anda:",
        reply_markup=markup
    )
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")

    
# --- Handler Role & NLP Input ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id
    
    # Menangani pemilihan role pertama kali
    if text in ["pengguna biasa", "pedagang"]:
        db.set_user_role(user_id, text)
        try:
            await update.message.reply_text(f"✅ Anda telah terdaftar sebagai '{text}'.\n")
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return

        # Menyediakan menu setelah role dipilih
        if text == "pengguna biasa":
            keyboard = [["Chat","/saldo", "/history", "/history_today", "/history_kategori"]]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            try:
                await update.message.reply_text(
                    "Selamat datang, Pengguna Biasa! Pilih perintah yang ingin Anda gunakan:\nContoh:\n/saldo",
                    reply_markup=markup
                )
            except httpx.ConnectTimeout:
                print("Timeout saat mengirim pesan ke Telegram.")
                return
        
        elif text == "pedagang":
            keyboard = [["Chat","/saldo", "/history", "/history_today", "/export_mingguan", "/export_bulanan", "/export_tahunan"]]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            try:
                await update.message.reply_text(
                    "Selamat datang, Pedagang! Pilih perintah yang ingin Anda gunakan:\nContoh:\n/export_mingguan",
                    reply_markup=markup
                )
            except httpx.ConnectTimeout:
                print("Timeout saat mengirim pesan ke Telegram.")
                return
        return
    if text == "chat":
        try:
            await update.message.reply_text("Silakan kirimkan pesan transaksi Anda.\nContoh:\nrisol terjual 50rb")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    
    # Cek role jika sudah ada dan lanjutkan input transaksi
    role = db.get_or_create_user_role(user_id)
    
    if not role:
        try:
            await update.message.reply_text("Silakan pilih jenis pengguna Anda terlebih dahulu.")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    
    # Menyediakan menu yang berbeda tergantung pada peran yang sudah dipilih
    if role == "pengguna biasa":
        try:    
            await update.message.reply_text("Anda memilih sebagai Pengguna Biasa. Berikut beberapa perintah yang dapat Anda gunakan:\n"
                                        "/chat - Kirimkan transaksi Anda Menggunakan Pesan\n"
                                        "/saldo - Cek saldo Anda\n"
                                        "/history - Lihat riwayat transaksi Anda\n"
                                        "/history_today - Transaksi hari ini\n"
                                        "/history_kategori [kategori] - Riwayat berdasarkan kategori")
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    elif role == "pedagang":
        try:
            await update.message.reply_text("Anda memilih sebagai Pedagang. Berikut beberapa perintah yang dapat Anda gunakan:\n"
                                        "/chat - Kirimkan transaksi Anda Menggunakan Pesan\n"
                                        "/saldo - Cek saldo Anda\n"
                                        "/history - Lihat riwayat transaksi Anda\n"
                                        "/history_today - Transaksi hari ini\n"
                                        "/export_mingguan - Laporan mingguan\n"
                                        "/export_bulanan - Laporan bulanan\n"
                                        "/export_tahunan - Laporan tahunan"
                                        "/hapus_hari_ini - Hapus semua transaksi hari ini\n"
                                        "/hapus_minggu_ini - Hapus semua transaksi minggu ini\n"
                                        "/hapus_semua - Hapus semua transaksi Anda")
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    
    # Pastikan data transaksi hanya diproses jika format input benar
    try:
        data = parse_transaksi(text)
    except ValueError:
        try:
            await update.message.reply_text("Format transaksi tidak valid. Silakan coba lagi.")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return

    db.insert_transaction(
        user_id=user_id,
        jumlah=data["jumlah"],
        kategori=data["kategori"],
        jenis=data["jenis"],
        catatan=data["catatan"]
    )
    try:
        await update.message.reply_text(f"✅ Transaksi '{data['kategori']}' sebesar Rp{data['jumlah']:,} telah dicatat.\nCatatan: {data['catatan']}")
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return

# --- Chat Handler --- 
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Pastikan teks transaksi dikirim
    if not text:
        try:
            await update.message.reply_text("Silakan kirimkan pesan transaksi Anda.\nContoh:\n/risol terjual 50rb")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    try:
        # Menyaring transaksi dengan NLP
        data = parse_transaksi(text)
    except ValueError:
        try:
            await update.message.reply_text("Format transaksi tidak valid. Silakan coba lagi dengan format yang benar.")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
        
    # Mencatat transaksi di database
    db.insert_transaction(
        user_id=user_id,
        jumlah=data["jumlah"],
        kategori=data["kategori"],
        jenis=data["jenis"],
        catatan=data["catatan"]
    )
    
    # Memberikan respon ke pengguna
    try:
        await update.message.reply_text(f"✅ Transaksi '{data['kategori']}' sebesar Rp{data['jumlah']:,} telah dicatat.\nCatatan: {data['catatan']}")
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return
    
# --- Saldo Command Handler ---
async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    summary = db.get_summary_by_user(user_id)

    if summary:
        msg = (
            f"📊 *Ringkasan Keuangan*\n"
            f"Total Masuk: Rp{summary['masuk']:,}\n"
            f"Total Keluar: Rp{summary['keluar']:,}\n"
            f"Saldo: Rp{summary['saldo']:,}\n"
        )
    else:
        msg = "Gagal mengambil data riwayat keuangan Anda."

    try:
        await update.message.reply_text(msg, parse_mode='Markdown')
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return
    
# --- History Handler ---
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    transactions = db.get_all_transactions_by_user(user_id)[:10]

    if not transactions:
        try:
            await update.message.reply_text("Tidak ada transaksi yang dicatat.")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    message = "*📂 Riwayat Transaksi:*\n\n"
    for i, trx in enumerate(transactions, 1):
        jumlah_fmt = f"Rp{trx['jumlah']:,}".replace(",", ".")
        message += (
            f"{i}. [{trx['jenis'].capitalize()}] - *{trx['kategori']}*\n"
            f"   Jumlah: {jumlah_fmt}\n"
            f"   Catatan: {trx['catatan'] or '-'}\n"
            f"   Tanggal: {trx['created_at'].strftime('%d/%m/%Y %H:%M')}\n\n"
        )
    try:
        await update.message.reply_text(message, parse_mode="Markdown")
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return
    
# --- History Today ---
async def history_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    transactions = db.get_today_transactions_by_user(user_id)

    if transactions:
        message = "*📅 Transaksi Hari Ini:*\n\n"
        for i, trx in enumerate(transactions, 1):
            jumlah_fmt = f"Rp{trx['jumlah']:,}".replace(",", ".")
            message += (
                f"{i}. [{trx['jenis'].capitalize()}] - *{trx['kategori']}*\n"
                f"   Jumlah: {jumlah_fmt}\n"
                f"   Catatan: {trx['catatan'] or '-'}\n"
                f"   Waktu: {trx['created_at'].strftime('%H:%M')}\n\n"
            )
    else:
        message = "Tidak ada transaksi yang dicatat hari ini."

    try:
        await update.message.reply_text(message, parse_mode="Markdown")
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return
    
# --- History Kategori ---
async def history_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) == 0:
        try:
            await update.message.reply_text("Harap masukkan kategori. Contoh:\n/history_kategori makan")
            return
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
        
    kategori = " ".join(context.args).lower()
    transactions = db.get_transactions_by_category(user_id, kategori)

    if transactions:
        message = f"*📂 Riwayat Transaksi Kategori '{kategori.title()}':*\n\n"
        for i, trx in enumerate(transactions, 1):
            jumlah_fmt = f"Rp{trx['jumlah']:,}".replace(",", ".")
            message += (
                f"{i}. [{trx['jenis'].capitalize()}]\n"
                f"   Jumlah: {jumlah_fmt}\n"
                f"   Catatan: {trx['catatan'] or '-'}\n"
                f"   Tanggal: {trx['created_at'].strftime('%d/%m/%Y %H:%M')}\n\n"
            )
    else:
        message = f"Tidak ada transaksi pada kategori '{kategori}'."

    try:
        await update.message.reply_text(message, parse_mode="Markdown")
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return
    
# --- Export Excel (mingguan, bulanan, tahunan) ---
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    command = update.message.text.lower()
    mode = command.replace("/export_", "")  # dapatkan mode: mingguan, bulanan, tahunan

    try:
        file_path = db.generate_excel_report(user_id, mode)
        await update.message.reply_document(
            open(file_path, 'rb'),
            caption=f"📊 Laporan {mode.capitalize()} Anda berhasil dibuat.",
        )
    except ValueError as e:
        try:
            await update.message.reply_text(str(e))
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
        
    except Exception as e:
        try:
            await update.message.reply_text("Terjadi kesalahan saat membuat laporan.")
            print(f"Error saat ekspor: {e}")
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    
# --- Delete Daily Transactions Command ---
async def delete_daily_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    command = update.message.text.lower()
    mode = command.replace("/hapus_", "")  # dapatkan mode: mingguan, bulanan, tahunan
    
    try:
        db.delete_daily_transactions(user_id)
        await update.message.reply_text("✅ Semua transaksi hari ini telah dihapus.")
    except Exception as e:
        await update.message.reply_text("Terjadi kesalahan saat menghapus transaksi.")
        print(f"Error saat menghapus transaksi: {e}")
    
# --- Delete Weekly Transactions Command ---
async def delete_weekly_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    command = update.message.text.lower()
    mode = command.replace("/hapus_", "")  # dapatkan mode: mingguan, bulanan, tahunan
    
    try:
        db.delete_weekly_transactions(user_id)
        try:
            await update.message.reply_text("✅ Semua transaksi minggu ini telah dihapus.")
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
    except Exception as e:
        try:
            await update.message.reply_text("Terjadi kesalahan saat menghapus transaksi.")
            print(f"Error saat menghapus transaksi: {e}")
        except httpx.ConnectTimeout:
            print("Timeout saat mengirim pesan ke Telegram.")
            return
        
# --- Delete All Transactions Command ---
async def delete_all_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        db.delete_all_transactions(user_id)
        await update.message.reply_text("✅ Semua transaksi Anda telah dihapus.")
    except Exception as e:
        await update.message.reply_text("Terjadi kesalahan saat menghapus transaksi.")
        print(f"Error saat menghapus transaksi: {e}")

# --- Help Command Handler ---
async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_list = "\n".join([f"{cmd}: {desc}" for cmd, desc in commands.items()])
    try:
        await update.message.reply_text(
            f"Daftar perintah yang tersedia:\n{command_list}"
        )
    except httpx.ConnectTimeout:
        print("Timeout saat mengirim pesan ke Telegram.")
        return

# Main function to run the bot
async def main():
    db.initialize_db()  # Pastikan fungsi ini memulai atau mempersiapkan DB
    app = ApplicationBuilder().token(config.BOT_TOKEN).connect_timeout(30).read_timeout(30).build()

    # Set up commands for the bot
    await app.bot.set_my_commands([BotCommand(command, description) for command, description in commands.items()])

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", show_commands))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("history_today", history_today))
    app.add_handler(CommandHandler("history_kategori", history_kategori))
    app.add_handler(CommandHandler("export_mingguan", export_excel))
    app.add_handler(CommandHandler("export_bulanan", export_excel))
    app.add_handler(CommandHandler("export_tahunan", export_excel))
    app.add_handler(CommandHandler("hapus_hari_ini", delete_daily_transactions))
    app.add_handler(CommandHandler("hapus_minggu_ini", delete_weekly_transactions))
    app.add_handler(CommandHandler("hapus_semua", delete_all_transactions))

    print("🤖 Bot berjalan...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Terjadi kesalahan saat menjalankan bot: {e}")
