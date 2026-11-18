import shutil
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
db_path = BASE_DIR / "crypto.db"
backup = BASE_DIR / "crypto_backup2.db"  # ชื่อใหม่ ไม่ทับ crypto_backup.db อันเดิม

if backup.exists():
    print("มีไฟล์สำรอง crypto_backup2.db อยู่แล้ว แปลว่าเคยรันไปแล้ว หยุดเพื่อกันแก้ซ้ำ")
    raise SystemExit(0)

shutil.copy(db_path, backup)
print("สำรอง crypto_backup2.db เรียบร้อย")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# ขั้น 1: ดูตัวอย่างก่อน
cur.execute("""
    SELECT id, timestamp, datetime(timestamp, '-7 hours')
    FROM price_snapshot
    WHERE id IN (62, 85)
""")
print("ก่อนแก้ -> ตัวอย่างที่จะแก้:", cur.fetchall())

# ขั้น 2: แก้จริง (แก้เครื่องหมายคำพูดให้เป็น '-7 hours' ทั้งสองฝั่ง)
cur.execute("""
    UPDATE price_snapshot
    SET timestamp = datetime(timestamp, '-7 hours')
    WHERE id IN (62, 85)
      AND timestamp IN ('2026-11-15 19:26:01', '2026-11-15 21:01:55')
""")
print("แก้ไป", cur.rowcount, "แถว")     # ต้องได้ 2

conn.commit()
conn.close()
