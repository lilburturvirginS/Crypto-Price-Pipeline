import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "crypto.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. สรุปภาพรวมทั้งหมด (หลังจุดซ่อม id > 27)
cur.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM price_snapshot WHERE id > 27")
print("แถวทั้งหมด (id > 27):", cur.fetchone())

# 2. สรุปแยกตามเหรียญ
print("\n--- สรุปแยกตามเหรียญ (id > 27) ---")
cur.execute("""
    SELECT coin_name, COUNT(*), MIN(timestamp), MAX(timestamp)
    FROM price_snapshot
    WHERE id > 27
    GROUP BY coin_name
    ORDER BY coin_name
""")
for row in cur.fetchall():
    print(row)

# 3. สรุปรายวัน (แยกตามวันและเหรียญ)
print("\n--- สรุปรายวัน ---")
cur.execute("""
    SELECT substr(timestamp, 1, 10) AS day, coin_name, COUNT(*)
    FROM price_snapshot
    WHERE id > 27
    GROUP BY day, coin_name
    ORDER BY day, coin_name
""")
for row in cur.fetchall():
    print(row)

# 4. ตรวจช่องว่างแยกทีละเหรียญ (จับทั้งช่วงข้อมูลขาด > 20 นาที และเวลาย้อนหลัง < 0)
cur.execute("SELECT DISTINCT coin_name FROM price_snapshot WHERE id > 27 ORDER BY coin_name")
coins = [r[0] for r in cur.fetchall()]

for coin in coins:
    print(f"\n--- ตรวจช่องว่าง: {coin} ---")
    cur.execute(
        "SELECT timestamp FROM price_snapshot WHERE id > 27 AND coin_name = ? ORDER BY id",
        (coin,),
    )
    times = [datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S") for r in cur.fetchall()]
    found_gap = False
    for prev, curr in zip(times, times[1:]):
        gap_min = (curr - prev).total_seconds() / 60
        if gap_min > 20 or gap_min < 0:
            print(prev, "→", curr, f"ห่าง {gap_min:.0f} นาที")
            found_gap = True
    if not found_gap:
        print("ไม่พบช่องว่างผิดปกติ")

conn.close()
