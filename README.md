# 📈 IDX Auto Watcher (Announcement & Financial Report)

Automated Python system for monitoring **corporate announcements** and **financial statements (PDF)** from the [Indonesia Stock Exchange (IDX)](https://www.idx.co.id), then sending instant Telegram notifications whenever new data appears.

---

## ✨ Features
- 📰 Fetches **Corporate Actions** via `GetAnnouncement` endpoint  
- 📊 Fetches **Financial Statements** (only `FinancialStatement-YYYY-TWn-XXXX.pdf`) via `GetFinancialReport` endpoint  
- 🧠 Uses **SQLite cache** to prevent duplicate notifications  
- 🤖 Sends formatted updates directly to **Telegram Bot**  
- 🕵️‍♂️ **Playwright fallback** when Cloudflare blocks direct requests  
- ⏰ Auto-loops every few minutes (configurable)  

---

## 📂 Project Structure

```
idx-watcher/
│
├── get_announcement.py          # Monitors corporate announcements
├── get_financial_report.py      # Monitors financial reports (FinancialStatement PDFs)
├── run_get_announcement.bat     # Windows startup script for announcement watcher
├── run_get_financial_report.bat # Windows startup script for financial watcher
├── requirements.txt             # Python dependencies
├── announcement_cache.db        # SQLite cache (auto-created)
├── financial_cache.db           # SQLite cache (auto-created)
└── README.md                    # Project documentation
```

---

## ⚙️ Requirements

- **Python 3.10+**
- **Windows VPS or PC**
- **Internet access**
- **Telegram Bot Token** + **Chat ID**

---

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/idx-watcher.git
cd idx-watcher
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Telegram Credentials
Edit both `.py` files:
```python
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = 1234567890
```

---

## ▶️ Running the Scripts

### Option 1 — Manual (CMD)
```bash
python get_announcement.py
python get_financial_report.py
```

### Option 2 — Windows .BAT (Recommended)
Double-click either:
- `run_get_announcement.bat`
- `run_get_financial_report.bat`

Each script runs indefinitely, checking every 5 minutes.

### Option 3 — Task Scheduler (Auto-Start on Boot)
1. Open **Task Scheduler**
2. **Create Task → Actions → Start a program**
3. Point to one of the `.bat` files
4. Set trigger → “At system startup” or “Every 5 minutes”

---

## 💬 Telegram Output Examples

### Announcement
```
🏦 <b>BUVA</b> (Announcement)
📅 2025-10-28
📄 Keterbukaan Informasi terkait Aksi Korporasi - Rencana Penambahan Modal
🔗 https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/...
```

### Financial Report
```
🏦 <b>ABBA</b> (Financial Statement)
📅 2025-10-28
📄 Financial Statement TW1 2025 - Mahaka Media Tbk (ABBA)
🔗 https://www.idx.co.id/.../Laporan%20Keuangan%20Tahun%202025/TW1/ABBA/FinancialStatement-2025-I-ABBA.pdf
```

---

## 🧩 How It Works

1. Fetch JSON from IDX public endpoints  
   - `GetAnnouncement`
   - `GetFinancialReport`
2. Parse and filter data:
   - Only top 5 newest items  
   - FinancialStatement PDFs only  
3. Check local SQLite DB to prevent duplicates  
4. Send formatted Telegram messages  
5. Wait 5 minutes → repeat loop  

If blocked by Cloudflare → automatically retries using **Playwright headless Chromium**.

---

## 🗂️ Database Schema

Each script has its own `.db` file.

| Column | Description |
|--------|--------------|
| `id` | Unique identifier |
| `title` | Announcement or report title |
| `kode` | Stock ticker |
| `tanggal` | Publication date |
| `link` | Direct PDF URL |
| `source` | “Announcement” / “Financial Statement” |
| `first_seen` | First detection date |
| `last_sent` | Last sent date (prevents duplicates) |

---

## ⚙️ Configuration

Modify these constants at the top of each script if needed:

```python
POLL_INTERVAL_MINUTES = 5   # Interval between checks
DB_PATH = "financial_cache.db"  # or announcement_cache.db
```

---

## 🧪 Testing
Run locally:
```bash
python get_financial_report.py
```
If successful, you should see logs like:
```
Financial Statement: 3 new records.
Sent: AALI_FinancialStatement_TW1_2025
Sleeping 5 minutes...
```
and corresponding messages in Telegram.

---

## 🧰 Rebuild Environment

If sharing with others or deploying elsewhere:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 💡 Notes

- You can safely delete `.db` files anytime to reset history.
- URL encoding ensures links with spaces work correctly in Telegram.
- Both scripts can run simultaneously without conflict.

---

## 📄 License
MIT License — free for modification and distribution with attribution.

---

## 👨‍💻 Developed by
**ByteForge (Arka Diaksa)**  
Built using **Python 3**, **Requests**, and **Playwright**  
Tested on Windows Server 2019 VPS
