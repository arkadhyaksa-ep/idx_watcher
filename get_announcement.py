import time
import json
import sqlite3
import datetime
from typing import List, Dict, Optional

import requests

# optional fallback Playwright for Cloudflare protection
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

TELEGRAM_TOKEN = "Masukkan Token Telegram Bot anda"
TELEGRAM_CHAT_ID = "Masukkan Chat ID anda tanpa tanda kutip"
IDX_ANNOUNCE_URL = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement?kodeEmiten=&emitenType=*&indexFrom=0&pageSize=10&dateFrom=19010101&dateTo=20251028&lang=id&keyword=Aksi+korporasi"
POLL_INTERVAL_MINUTES = 5

DB_PATH = "announcement_cache.db"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


# === Database ===
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
    """Save new records and return list of new items."""
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


# === Telegram ===
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


# === Fetch functions ===
def fetch_idx_requests(url: str) -> Optional[dict]:
    """Try direct GET request."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        print("Failed (status):", resp.status_code)
        return None
    except Exception as e:
        print("Request error:", e)
        return None


def fetch_idx_playwright(url: str) -> Optional[dict]:
    """Fallback via headless browser if Cloudflare blocks request."""
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
                if url in response.url and "application/json" in (response.headers.get("content-type","") or ""):
                    text = response.text()
                    result_holder["json"] = json.loads(text)
            except Exception:
                pass

        page.on("response", handle_response)
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
        except Exception as e:
            print("Playwright error:", e)
        browser.close()
        return result_holder.get("json")


# === Parsing JSON ===
def parse_announcement_json(data: dict, source_name="Announcement") -> List[Dict]:
    out = []
    if not data or "Replies" not in data:
        return out

    for item in data["Replies"]:
        peng = item.get("pengumuman", {})
        attach = item.get("attachments", [])
        link_pdf = attach[0]["FullSavePath"] if attach else None

        out.append({
            "Judul": peng.get("JudulPengumuman"),
            "KodeEmiten": peng.get("Kode_Emiten", "").strip(),
            "Tanggal": peng.get("TglPengumuman"),
            "FileUrl": link_pdf,
            "Source": source_name
        })
    return out


def parse_financial_json(data: dict, source_name="Financial") -> List[Dict]:
    out = []
    if not data or "Replies" not in data:
        return out

    for item in data["Replies"]:
        kode = item.get("KodeEmiten") or item.get("kodeEmiten")
        tanggal = item.get("TanggalLaporan") or item.get("date") or ""
        judul = item.get("JudulLaporan") or item.get("judul") or "Laporan Keuangan"
        link = item.get("FileUrl") or item.get("link") or None

        out.append({
            "Judul": judul,
            "KodeEmiten": kode.strip() if kode else "",
            "Tanggal": tanggal,
            "FileUrl": link,
            "Source": source_name
        })
    return out


# === Utility ===
def build_message(rec: Dict) -> str:
    title = rec.get("Judul") or "-"
    kode = rec.get("KodeEmiten") or "-"
    tanggal = rec.get("Tanggal") or "-"
    link = rec.get("FileUrl") or "-"
    source = rec.get("Source") or ""
    text = f"🏦 <b>{kode}</b> ({source})\n📅 {tanggal}\n📄 {title}\n🔗 {link}"
    return text


# === Main loop ===
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
    print("=== IDX Watcher started ===")
    while True:
        print("\n=== Checking at", datetime.datetime.now().isoformat(), "===")
        if IDX_ANNOUNCE_URL:
            process_endpoint(IDX_ANNOUNCE_URL, parse_announcement_json, "Announcement")
        print(f"Sleeping {POLL_INTERVAL_MINUTES} minutes...")
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
