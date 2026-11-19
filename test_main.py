import sqlite3
import main 
import requests

def test_save_price(tmp_path,monkeypatch):
    #1.สร้าง path ไฟล์ db ชั่วคราว
    fake_db = tmp_path / "test.db" 

    #2.สลับ main.DB_PATH ให้ชี้ไปที่ fake_db ชั่วคราว
    monkeypatch.setattr(main,"DB_PATH",fake_db) 

    #3.สร้างตารางแล้วบันทึกข้อมูลจำลอง 1 แถว
    main.init_db() 
    main.save_price('bitcoin', 1000.5, "usd")

    #4.อ่านจาก fake_db กลับมาเช็ค
    with sqlite3.connect(fake_db) as conn: 
        rows = conn.execute("SELECT coin_name,price,currency FROM price_snapshot").fetchall()

    # 5.ยืนยันผลด้วย assert (ถ้าไม่ตรง pytest จะฟ้อง FAILED ทันที)
    assert len(rows) == 1  
    assert rows[0] == ('bitcoin', 1000.5, 'usd')

def test_fetch_price_normalizes_and_skips_unknown(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass  # จำลองว่าได้ HTTP 200 ปกติ

        def json(self):
            return {"bitcoin": {"usd": 65000}, "ethereum": {"usd": 1800}}

    # สลับ requests.get ใน main ให้คืน FakeResponse แทนการยิงเน็ตจริง
    monkeypatch.setattr(main.requests, "get", lambda *args, **kwargs: FakeResponse())

    # ส่งทั้งตัวพิมพ์ใหญ่ ("Bitcoin") และเหรียญปลอม ("fake_coin") เข้าไปทดสอบ
    result = main.fetch_price(["Bitcoin", "ethereum", "fake_coin"])

    # ตรวจว่าผลลัพธ์ต้องเหลือเฉพาะเหรียญที่มีอยู่จริง และ key เป็นตัวพิมพ์เล็ก
    assert result == {'bitcoin':65000,'ethereum':1800}

def test_fetch_with_retry_recovers_after_error(monkeypatch):
    calls = 0

    def fake_fetch(coins):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise requests.exceptions.ConnectionError("เน็ตหลุดจำลอง")
        return {"bitcoin": 70000}

    # 1. สลับ main.fetch_price เป็นตัวจำลองที่พังรอบแรกแล้วผ่านรอบสอง
    monkeypatch.setattr(main, "fetch_price", fake_fetch)
    # 2. ปิด time.sleep ชั่วคราว เพื่อไม่ให้เทสต้องรอ 5 วินาทีจริง
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)

    result = main.fetch_with_retry(["bitcoin"], max_attempts=3)

    # 3. เติม assert เอง: ผลลัพธ์ต้องได้อะไร และ fake_fetch ควรถูกเรียกไปทั้งหมดกี่ครั้ง?
    assert result == {"bitcoin":70000}
    assert calls == 2