import csv
import sqlite3
from pathlib import Path

# กำหนด path เต็มจากตำแหน่งไฟล์นี้ เพื่อไม่ให้พังเวลารันจากโฟลเดอร์อื่น
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "crypto.db"
EXPORT_DIR = BASE_DIR / "exports"


def export_snapshots(conn: sqlite3.Connection) -> Path:
    """ส่งออกข้อมูลราย snapshot (id > 27) พร้อมเวลาไทยและ % เปลี่ยนแปลง เป็น CSV สำหรับ Power BI"""
    EXPORT_DIR.mkdir(exist_ok=True)  # สร้างโฟลเดอร์ exports ถ้ายังไม่มี (มีแล้วไม่ error)
    out_path = EXPORT_DIR / "crypto_snapshots.csv"

    query = """
    SELECT
        id,
        coin_name,
        price,
        currency,
        timestamp AS timestamp_utc,
        datetime(timestamp, '+7 hours') AS timestamp_bkk, -- แปลง UTC เป็นเวลาไทย
        LAG(price) OVER (PARTITION BY coin_name ORDER BY timestamp) AS prev_price,
        ROUND(
            (price - LAG(price) OVER (PARTITION BY coin_name ORDER BY timestamp)) * 100.0
            / NULLIF(LAG(price) OVER (PARTITION BY coin_name ORDER BY timestamp), 0), -- กันหารด้วย 0
            4
        ) AS pct_change
    FROM price_snapshot
    WHERE id > 27
    ORDER BY timestamp, coin_name
    """
    cur = conn.execute(query)
    headers = [desc[0] for desc in cur.description]  # ดึงชื่อคอลัมน์จากผลลัพธ์ SQL อัตโนมัติ
    rows = cur.fetchall()

    # ใช้ encoding="utf-8-sig" (UTF-8 แบบมี BOM) เพื่อให้ทั้ง Excel และ Power BI อ่านได้ไม่เพี้ยน
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return out_path


def export_hourly_summary(conn: sqlite3.Connection) -> Path:
    """ส่งออกตารางสรุปรายชั่วโมง (เฉลี่ย, ต่ำสุด, สูงสุด, จำนวนรอบ) เป็น CSV สำหรับ Power BI"""
    EXPORT_DIR.mkdir(exist_ok=True)
    out_path = EXPORT_DIR / "crypto_hourly.csv"

    query = """
    SELECT
        coin_name,
        substr(datetime(timestamp, '+7 hours'), 1, 13) || ':00' AS hour_bkk,
        ROUND(AVG(price), 2) AS avg_price,
        MIN(price) AS low_price,
        MAX(price) AS high_price,
        COUNT(*) AS snapshots
    FROM price_snapshot
    WHERE id > 27
    GROUP BY coin_name, hour_bkk
    ORDER BY hour_bkk, coin_name
    """
    cur = conn.execute(query)
    headers = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return out_path


def main():
    with sqlite3.connect(DB_PATH) as conn:
        snap_path = export_snapshots(conn)
        hourly_path = export_hourly_summary(conn)
    print(f"Exported snapshots -> {snap_path}")
    print(f"Exported hourly    -> {hourly_path}")


if __name__ == "__main__":
    main()
