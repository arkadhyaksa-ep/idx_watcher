📄 Deskripsi Singkat

Sistem ini akan secara otomatis mengambil data keterbukaan informasi dan laporan keuangan dari situs resmi Bursa Efek Indonesia (IDX), lalu mengirimkan notifikasi ke Telegram setiap kali ada pengumuman atau laporan baru.

Terdiri dari dua script utama:

get_announcement.py → memantau aksi korporasi

get_financial_report.py → memantau laporan keuangan (FinancialStatement PDF)

⚙️ Persyaratan Sistem

Pastikan VPS Windows Anda sudah memiliki:

Python 3.10 atau lebih baru

Koneksi internet stabil

Telegram Bot Token dan Chat ID

🧩 Langkah Instalasi
1. Install dependensi Python

Buka Command Prompt (CMD), lalu jalankan:

pip install requests playwright
playwright install chromium

2. Siapkan file proyek

Ekstrak semua file ke satu folder, misalnya:

C:\idx-watcher\


Isi folder:

get_announcement.py
get_financial_report.py
run_get_announcement.bat
run_get_financial_report.bat
README.txt

3. Edit token Telegram (jika perlu)

Buka file .py menggunakan teks editor (misal: Notepad), dan ubah dua variabel ini di bagian atas:

TELEGRAM_TOKEN = "ISI_DENGAN_TOKEN_BOT_ANDA"
TELEGRAM_CHAT_ID = ISI_DENGAN_CHAT_ID_ANDA

▶️ Cara Menjalankan
Pilihan 1 — Manual

Klik dua kali file .bat:

run_get_announcement.bat → memantau aksi korporasi

run_get_financial_report.bat → memantau laporan keuangan

Kedua script akan berjalan otomatis dan memeriksa data setiap 5 menit.

Pilihan 2 — Otomatis (disarankan)

Agar berjalan terus walau VPS restart:

Buka menu Task Scheduler di Windows.

Pilih Create Task → Actions → Start a program

Arahkan ke file .bat (contoh: C:\idx-watcher\run_get_financial_report.bat)

Set trigger ke At startup atau Every 5 minutes

💬 Format Notifikasi di Telegram

Contoh pesan:

🏦 <b>BBRI</b> (Financial Statement)
📅 2025-10-28
📄 Financial Statement TW1 2025 - Bank Rakyat Indonesia (BBRI)
🔗 https://www.idx.co.id/.../FinancialStatement-2025-I-BBRI.pdf


atau untuk pengumuman:

🏦 <b>BUVA</b> (Announcement)
📅 2025-10-28
📄 Keterbukaan Informasi terkait Aksi Korporasi - Rencana Penambahan Modal
🔗 https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/...

🗂️ Database Cache

Setiap script akan otomatis membuat file SQLite:

announcement_cache.db

financial_cache.db

Fungsi: menyimpan data yang sudah dikirim agar tidak duplikat setiap kali dijalankan.

Jika ingin memulai dari awal (reset):

Tutup script.

Hapus file .db.

Jalankan ulang script.

💡 Catatan Teknis Tambahan

Jika koneksi ke IDX diblokir oleh Cloudflare, sistem otomatis beralih ke Playwright headless browser.

URL laporan yang memiliki spasi otomatis dikonversi agar valid di Telegram.

Interval pengecekan dapat diubah di bagian atas file (POLL_INTERVAL_MINUTES).