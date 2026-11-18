import shutil
import sqlite3
from pathlib import Path

backup = Path("crypto_backup.db")
if backup.exists():
    print("มีไฟล์สำรองอยู่แล้ว แปลว่าเคยรันไปแล้ว หยุดเพื่อกันแก้ซ้ำ")
    raise SystemExit

shutil.copy("crypto.db", backup)          # ขั้น 1: สำรองก่อนแตะข้อมูล
print("สำรองเรียบร้อย")

conn = sqlite3.connect("crypto.db")
cur = conn.cursor()

# ขั้น 2: ดูตัวอย่างก่อน ว่าจะแก้อะไรเป็นอะไร (ยังไม่แก้จริง)
cur.execute("""
    SELECT id, timestamp, datetime(timestamp, '-7 hours')
    FROM price_snapshot
    WHERE id <= 27
""")
rows = cur.fetchall()
for r in rows:
    print(r)
print(f"จะแก้ทั้งหมด {len(rows)} แถว (ควรได้ 21)")

# ขั้น 3: ยืนยันก่อนแก้จริง
if input("พิมพ์ y เพื่อยืนยัน: ").strip().lower() == "y":
    cur.execute("""
        UPDATE price_snapshot
        SET timestamp = datetime(timestamp, '-7 hours')
        WHERE id <= 27
    """)
    conn.commit()
    print(f"แก้แล้ว {cur.rowcount} แถว")
else:
    print("ยกเลิก ไม่มีอะไรถูกแก้")

conn.close()