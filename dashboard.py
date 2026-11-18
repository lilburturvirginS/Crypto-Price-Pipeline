import sqlite3
from pathlib import Path

import altair as alt       # ไลบรารีวาดกราฟแบบโต้ตอบได้ (ติดมากับ Streamlit อยู่แล้ว)
import pandas as pd        # จัดการข้อมูลแบบตาราง (DataFrame)
import streamlit as st     # สร้างหน้าเว็บ Dashboard ด้วย Python ล้วน

# นำเข้าฟังก์ชันส่งออก CSV จากไฟล์ export_csv.py มาใช้ในปุ่มกดบนหน้าเว็บ
from export_csv import export_hourly_summary, export_snapshots

# อ้างอิง path เต็มจากตำแหน่งไฟล์นี้ เพื่อไม่ให้พังเวลาสั่งรันจากโฟลเดอร์อื่น
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "crypto.db"
LOG_PATH = BASE_DIR / "pipeline.log"

# ตั้งค่าหน้าเว็บ (ต้องเรียกเป็นคำสั่ง Streamlit แรกสุดของไฟล์)
st.set_page_config(
    page_title="Crypto Price Pipeline Dashboard",  # ชื่อบนแท็บเบราว์เซอร์
    page_icon="🪙",                                # ไอคอนบนแท็บ
    layout="wide",                                 # ขยายความกว้างเต็มหน้าจอ
)


def load_snapshots() -> pd.DataFrame:
    """ดึงข้อมูลราคาล่าสุด (หลังจุดซ่อม id > 27) พร้อมแปลงเวลาไทยและคำนวณ % เปลี่ยนแปลง"""
    # ใช้ CTE (WITH lagged AS ...) เพื่อคำนวณ prev_price ไว้ก่อน 1 ชั้น จะได้เอาไปคำนวณ % ต่อได้สะดวกไม่ต้องเขียน LAG ซ้ำ
    query = """
    WITH lagged AS (
        SELECT
            id,
            coin_name,
            price,
            currency,
            timestamp AS timestamp_utc,
            datetime(timestamp, '+7 hours') AS timestamp_bkk, -- แปลง UTC เป็นเวลาไทยตอนแสดงผล
            -- ดึงราคาของรอบก่อนหน้าในเหรียญเดียวกัน (แบ่งกลุ่มด้วย PARTITION BY และเรียงเวลาด้วย ORDER BY)
            LAG(price) OVER (PARTITION BY coin_name ORDER BY timestamp) AS prev_price
        FROM price_snapshot
        WHERE id > 27 -- ตัดข้อมูลทดลองช่วงแรกออก เอาเฉพาะข้อมูลที่เริ่มรันระบบจริง
    )
    SELECT
        id,
        coin_name,
        price,
        currency,
        timestamp_utc,
        timestamp_bkk,
        prev_price,
        -- คำนวณ % เปลี่ยนแปลง: (ใหม่ - เก่า) * 100 / เก่า
        -- NULLIF(prev_price, 0) กัน error หารด้วย 0 กรณีราคาเก่าเป็น 0
        ROUND((price - prev_price) * 100.0 / NULLIF(prev_price, 0), 4) AS pct_change
    FROM lagged
    ORDER BY timestamp_utc, coin_name
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn)  # รัน SQL แล้วแปลงผลลัพธ์เป็นตาราง pandas ทันที

    # แปลงคอลัมน์เวลาจากข้อความ (str) ให้เป็นชนิด datetime เพื่อใช้กรองวันที่และพล็อตกราฟเวลา
    df["timestamp_bkk"] = pd.to_datetime(df["timestamp_bkk"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    return df


def load_hourly_summary() -> pd.DataFrame:
    """สรุปข้อมูลรายชั่วโมง (เฉลี่ย, ต่ำสุด, สูงสุด, จำนวนรอบ) เป็นเวลาไทย"""
    query = """
    SELECT
        coin_name,
        -- ตัดเอา 13 ตัวแรก ('YYYY-MM-DD HH') แล้วต่อด้วย ':00' (เครื่องหมาย || คือการต่อข้อความใน SQLite)
        substr(datetime(timestamp, '+7 hours'), 1, 13) || ':00' AS hour_bkk,
        ROUND(AVG(price), 2) AS avg_price,
        MIN(price) AS low_price,
        MAX(price) AS high_price,
        COUNT(*) AS snapshots
    FROM price_snapshot
    WHERE id > 27
    GROUP BY coin_name, hour_bkk
    ORDER BY hour_bkk DESC, coin_name -- เรียงชั่วโมงล่าสุดขึ้นก่อน
    """
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


def load_recent_logs(tail_n: int = 30) -> list[str]:
    """อ่านเฉพาะ N บรรทัดสุดท้ายของ pipeline.log (ถ้ายังไม่มีไฟล์ให้คืน list ว่าง)"""
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-tail_n:]  # ตัดเอาเฉพาะ tail_n บรรทัดท้ายสุด


def main():
    st.title("🪙 Crypto Price Pipeline Dashboard")
    st.caption("ข้อมูลจาก SQLite (เก็บแบบ UTC → แสดงผลเป็นเวลาไทย UTC+7)")

    # ถ้ายังไม่มีไฟล์ DB ให้แจ้งเตือนแล้วหยุดทำงานหน้านี้
    if not DB_PATH.exists():
        st.error(f"ไม่พบฐานข้อมูล: {DB_PATH}")
        return

    # โหลดข้อมูลทั้ง 2 ตารางเตรียมไว้
    df = load_snapshots()
    hourly_df = load_hourly_summary()

    # แถบเมนูด้านซ้าย (Sidebar) สำหรับตัวกรองและปุ่มเครื่องมือ
    with st.sidebar:
        st.header("⚙️ ตัวกรอง & เครื่องมือ")
        if st.button("🔄 รีเฟรชข้อมูล", width="stretch"):
            st.rerun()  # สั่งโหลดหน้าเว็บใหม่ทั้งหมดเพื่อดึงข้อมูลล่าสุดจาก DB

        # ดึงรายชื่อเหรียญที่มีใน DB แบบไม่ซ้ำกัน แล้วเรียงตามตัวอักษร
        coins = sorted(df["coin_name"].unique().tolist())
        selected_coin = st.selectbox("เลือกเหรียญสำหรับกราฟราคา", coins, index=0)

        # หาวันแรกและวันสุดท้ายที่มีในข้อมูล เพื่อกำหนดขอบเขตปฏิทินเลือกช่วงวัน
        min_date = df["timestamp_bkk"].dt.date.min()
        max_date = df["timestamp_bkk"].dt.date.max()
        date_range = st.date_input(
            "ช่วงวันที่ (เวลาไทย)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        st.divider()
        st.subheader("📊 ส่งออกข้อมูล (Power BI)")
        if st.button("Export CSV สำหรับ Power BI", width="stretch"):
            with sqlite3.connect(DB_PATH) as conn:
                snap_path = export_snapshots(conn)
                hourly_path = export_hourly_summary(conn)
            st.success(f"ส่งออกแล้วที่โฟลเดอร์ exports/\n- {snap_path.name}\n- {hourly_path.name}")

    # ส่วนที่ 1: การ์ดตัวเลข KPI แสดงราคาล่าสุดของทุกเหรียญเรียงเป็นคอลัมน์
    st.subheader("📌 ราคาล่าสุด (เทียบกับรอบก่อนหน้า)")
    cols = st.columns(len(coins))  # แบ่งคอลัมน์อัตโนมัติตามจำนวนเหรียญ (ตอนนี้คือ 3 ช่อง)
    for col, coin in zip(cols, coins):
        coin_df = df[df["coin_name"] == coin]
        latest = coin_df.iloc[-1]  # แถวสุดท้าย = ข้อมูลเวลาล่าสุดของเหรียญนั้น
        delta_pct = latest["pct_change"]
        # ถ้าเป็นแถวแรกสุดจะยังไม่มี prev_price (เป็น NaN) จึงไม่ต้องแสดง delta
        delta_str = f"{delta_pct:+.3f}%" if pd.notna(delta_pct) else None
        col.metric(
            label=f"{coin.upper()} (อัปเดต {latest['timestamp_bkk'].strftime('%d/%m %H:%M')} น.)",
            value=f"${latest['price']:,.2f}",
            delta=delta_str,
        )

    # กรองข้อมูลสำหรับวาดกราฟตามเหรียญและช่วงวันที่ที่ผู้ใช้เลือก
    filtered = df[df["coin_name"] == selected_coin].copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        filtered = filtered[
            (filtered["timestamp_bkk"].dt.date >= start_d)
            & (filtered["timestamp_bkk"].dt.date <= end_d)
        ]

    # ส่วนที่ 2: กราฟเส้นแสดงแนวโน้มราคา
    st.subheader(f"📈 แนวโน้มราคา {selected_coin.upper()} (เวลาไทย)")
    if filtered.empty:
        st.info("ไม่มีข้อมูลในช่วงวันที่ที่เลือก")
    else:
        # ใช้ Altair วาดกราฟ (:T = ชนิดเวลา Temporal, :Q = ชนิดตัวเลข Quantitative)
        chart = (
            alt.Chart(filtered)
            .mark_line(point=True)  # กราฟเส้นพร้อมจุดกลมแต่ละ snapshot
            .encode(
                x=alt.X("timestamp_bkk:T", title="เวลา (ไทย UTC+7)"),
                # zero=False สำคัญมาก: ไม่บังคับให้แกน Y เริ่มจาก 0 เพื่อให้เห็นความขึ้นลงของราคาชัดๆ
                y=alt.Y("price:Q", title="ราคา (USD)", scale=alt.Scale(zero=False)),
                # ข้อความที่เด้งขึ้นมาเวลาเอาเมาส์ชี้บนจุด
                tooltip=[
                    alt.Tooltip("timestamp_bkk:T", title="เวลาไทย", format="%Y-%m-%d %H:%M:%S"),
                    alt.Tooltip("price:Q", title="ราคา (USD)", format=",.2f"),
                    alt.Tooltip("pct_change:Q", title="% เปลี่ยนแปลง", format="+.4f"),
                ],
            )
            .properties(height=360)
            .interactive()  # เปิดให้ซูมและลากเลื่อนกราฟด้วยเมาส์ได้
        )
        st.altair_chart(chart, width="stretch")

    # ส่วนที่ 3: แบ่งหน้าจอล่างเป็น 2 ฝั่ง (ซ้ายกว้าง 3 ส่วน: ตารางรายชั่วโมง, ขวากว้าง 2 ส่วน: สถานะ Log)
    left, right = st.columns([3, 2])

    with left:
        st.subheader("⏱️ สรุปรายชั่วโมง (Hourly Summary)")
        coin_hourly = hourly_df[hourly_df["coin_name"] == selected_coin]
        st.dataframe(coin_hourly, width="stretch", hide_index=True)

    with right:
        st.subheader("🩺 สถานะ Pipeline (จาก pipeline.log)")
        logs = load_recent_logs(25)
        if not logs:
            st.info("ยังไม่มีไฟล์ pipeline.log")
        else:
            # นับจำนวนบรรทัดที่มีคำว่า WARNING และ ERROR ใน 25 บรรทัดล่าสุด
            warn_cnt = sum(" WARNING " in line for line in logs)
            err_cnt = sum(" ERROR " in line for line in logs)
            c1, c2, c3 = st.columns(3)
            c1.metric("จำนวนแถว DB", len(df))
            c2.metric("WARNING (25 ล่าสุด)", warn_cnt)
            c3.metric("ERROR (25 ล่าสุด)", err_cnt)
            # แสดง 12 บรรทัดล่าสุดของ log ในกล่องข้อความแบบโค้ด
            st.code("\n".join(logs[-12:]), language="text")


if __name__ == "__main__":
    main()
