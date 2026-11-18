import sqlite3
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler

import requests

DB_PATH = Path(__file__).parent / "crypto.db"   # path เต็ม ไม่ขึ้นกับว่ารันจากโฟลเดอร์ไหน
LOG_PATH = Path(__file__).parent / "pipeline.log"   # path เต็มของไฟล์ log ให้อยู่ที่โฟลเดอร์โปรเจกต์เสมอ
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS price_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_name TEXT, price REAL, currency TEXT, timestamp DATETIME
        )""")

coins = ['bitcoin','ethereum','solana']

def fetch_price(coins):
    coins = [c.lower() for c in coins] # กันตัวพิมพ์ใหญ่
    ids = ','.join(coins)
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": ids, "vs_currencies": "usd"},
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()

    prices = {}
    for coin in coins:
        if coin not in data:
            logging.warning(f"API ไม่รู้จักเหรียญ: {coin}")
            continue
        prices[coin] = data[coin]['usd']
    return prices

def fetch_with_retry(coins, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        try:
            return fetch_price(coins)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code not in RETRYABLE_STATUS:
                raise
            logging.warning(f"ครั้งที่ {attempt} ล้มเหลว (HTTP {e.response.status_code})")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logging.warning(f"ครั้งที่ {attempt} ล้มเหลว ({type(e).__name__})")
        if attempt < max_attempts:
            time.sleep(5 * 2 ** (attempt - 1))
    return None

def save_price(coin, price, currency="usd"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")   # เก็บเป็น UTC
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO price_snapshot (coin_name, price, currency, timestamp) VALUES (?, ?, ?, ?)",
            (coin, price, currency, ts))

def main():
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=1000000,
        backupCount=3,
        encoding='utf-8'                                # บันทึกไฟล์เป็น UTF-8 เพื่อรองรับภาษาไทย
    )
    logging.basicConfig(
        level=logging.INFO,                             # เก็บ log ตั้งแต่ระดับ INFO ขึ้นไป (INFO, WARNING, ERROR, CRITICAL)
        format="%(asctime)s %(levelname)s %(message)s", # รูปแบบข้อความ: เวลา | ระดับ | ข้อความ
        handlers=[handler]          
    )
    logging.Formatter.converter = time.gmtime
    logging.info('เริ่มรอบ')
    try:
        init_db()
        prices = fetch_with_retry(coins)
        if prices is None:
            logging.error(f"ยอมแพ้รอบนี้: {coins} ลองครบ 3 ครั้งแล้วยังดึงราคาไม่ได้")
            return 1
        if not prices:
            logging.error("ไม่พบราคาของเหรียญใดเลย (เช็คชื่อเหรียญใน coins)")
            return 1
        try:
            for coin, price in prices.items():
                save_price(coin, price, "usd")
                logging.info(f"บันทึก {coin} {price} USD")
            return 0
        except sqlite3.Error as e:
            logging.exception(f"บันทึกลง DB ไม่ได้: {e}")
            return 1
    except Exception:
        logging.exception("รอบนี้พังด้วย error ที่ไม่ได้คาดไว้")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())    