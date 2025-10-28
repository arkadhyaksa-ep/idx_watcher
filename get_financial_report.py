import time
import json
import sqlite3
import datetime
from typing import List, Dict, Optional
from urllib.parse import quote
import requests

# optional fallback Playwright for Cloudflare
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# === CONFIG ===
TELEGRAM_TOKEN = "Masukkan Token Telegram Bot anda"
TELEGRAM_CHAT_ID = "Masukkan Chat ID anda tanpa tanda kutip"

IDX_FINANCIAL_URL = (
    "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport?"
    "indexFrom=1&pageSize=50&year=2025&reportType=rdf&EmitenType=s&periode=tw1&"
    "kodeEmiten=&SortColumn=KodeEmiten&SortOrder=asc"
)

POLL_INTERVAL_MINUTES = 5
DB_PATH = "financial_cache.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# === DATABASE ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS announces (
        id TEXT PRIMARY KEY,
        title TEXT,
        kode TEXT,
        tanggal TEXT,
        link TEXT,
        source TEXT,
        first_seen DATE,
        last_sent DATE
    )""")
    conn.commit()
    conn.close()


def save_new_records(records: List[Dict]) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    new = []
    for r in records:
        rec_id = f"{r.get('KodeEmiten','')}_{r.get('Judul','')}_{r.get('Tanggal','')}_{r.get('Source','')}"
        rec_id = rec_id.strip()[:200]
        cur.execute("SELECT 1 FROM announces WHERE id = ?", (rec_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO announces (id, title, kode, tanggal, link, source, first_seen, last_sent) VALUES (?,?,?,?,?,?,?,?)",
                (
                    rec_id,
                    r.get("Judul"),
                    r.get("KodeEmiten"),
                    r.get("Tanggal"),
                    r.get("FileUrl"),
                    r.get("Source"),
                    datetime.date.today().isoformat(),
                    None,
                ),
            )
            new.append({**r, "id": rec_id})
    conn.commit()
    conn.close()
    return new


def mark_sent_today(rec_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE announces SET last_sent = ? WHERE id = ?", (datetime.date.today().isoformat(), rec_id))
    conn.commit()
    conn.close()


def was_sent_today(rec_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT last_sent FROM announces WHERE id = ?", (rec_id,))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return row[0] == datetime.date.today().isoformat()
    return False


# === TELEGRAM ===
def send_telegram_message(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print("Failed send telegram:", e)
        return False


# === FETCH ===
def fetch_idx_requests(url: str) -> Optional[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        if resp.status_code == 200:
            return resp.json()
        print("Failed (status):", resp.status_code)
        return None
    except Exception as e:
        print("Request error:", e)
        return None


def fetch_idx_playwright(url: str) -> Optional[dict]:
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available.")
        return None

    print("Using Playwright fallback for:", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = context.new_page()
        result_holder = {"json": None}

        def handle_response(response):
            try:
                if "GetFinancialReport" in response.url and "application/json" in (response.headers.get("content-type", "") or ""):
                    result_holder["json"] = json.loads(response.text())
            except Exception:
                pass

        page.on("response", handle_response)
        try:
            page.goto(url, wait_until="networkidle", timeout=40000)
            time.sleep(1)
        except Exception as e:
            print("Playwright error:", e)
        browser.close()
        return result_holder.get("json")


# === PARSER ===
def parse_financial_json(data: dict, source_name="Financial Statement") -> List[Dict]:
    out = []
    if not data or "Results" not in data:
        return out

    for item in data["Results"]:
        kode = item.get("KodeEmiten", "").strip()
        nama = item.get("NamaEmiten", "").strip()
        tanggal = item.get("File_Modified", "")[:10]
        periode = item.get("Report_Period", "")
        tahun = item.get("Report_Year", "")

        # Cari attachment yang mengandung "FinancialStatement"
        link_pdf = None
        attachments = item.get("Attachments", [])
        for att in attachments:
            filename = att.get("File_Name") or att.get("FilePath") or att.get("File_Path", "")
            if not filename:
                continue
            if "FinancialStatement" in filename and filename.endswith(".pdf"):
                path = att.get("File_Path") or att.get("FilePath")
                if not path:
                    continue

                # pastikan URL valid
                if not path.startswith("http"):
                    path = f"https://www.idx.co.id{path}"

                # encode spasi dan karakter khusus
                safe_path = quote(path, safe=":/%._-")
                link_pdf = safe_path
                break

        if not link_pdf:
            continue

        judul = f"Financial Statement {periode.upper()} {tahun} - {nama} ({kode})"

        out.append({
            "Judul": judul,
            "KodeEmiten": kode,
            "Tanggal": tanggal,
            "FileUrl": link_pdf,
            "Source": source_name
        })
    return out


# === UTIL ===
def build_message(rec: Dict) -> str:
    kode = rec.get("KodeEmiten", "-")
    tanggal = rec.get("Tanggal", "-")
    title = rec.get("Judul", "-")
    link = rec.get("FileUrl", "-")
    source = rec.get("Source", "")
    return f"🏦 <b>{kode}</b> ({source})\n📅 {tanggal}\n📄 {title}\n🔗 {link}"


# === MAIN ===
def process_endpoint(url: str, parser_func, source_name: str):
    data = fetch_idx_requests(url)
    if data is None:
        data = fetch_idx_playwright(url)

    items = parser_func(data, source_name=source_name) if data else []
    if not items:
        print(f"No items parsed from {source_name}.")
        return

    top5 = items[:5]
    added = save_new_records(top5)
    print(f"{source_name}: {len(added)} new records.")
    for r in added:
        if not was_sent_today(r["id"]):
            msg = build_message(r)
            if send_telegram_message(msg):
                mark_sent_today(r["id"])
                print("Sent:", r["id"])
            else:
                print("Failed send:", r["id"])


def main():
    init_db()
    print("=== IDX Financial Statement Watcher started ===")
    while True:
        print("\n=== Checking at", datetime.datetime.now().isoformat(), "===")
        process_endpoint(IDX_FINANCIAL_URL, parse_financial_json, "Financial Statement")
        print(f"Sleeping {POLL_INTERVAL_MINUTES} minutes...")
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
