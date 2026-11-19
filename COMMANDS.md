# Command Cheat Sheet — Crypto Price Pipeline

รวมคำสั่ง PowerShell ทั้งหมดที่ใช้ทำงานกับโปรเจคนี้ (รันจากโฟลเดอร์ `C:\Users\CATOZ\Desktop\Pj`)

---

## 0. เข้าโฟลเดอร์โปรเจค

```powershell
cd C:\Users\CATOZ\Desktop\Pj
```

---

## 1. ดูข้อมูลล่าสุด + เปิด Dashboard + ส่งออก Power BI

```powershell
# ดึง crypto.db และ pipeline.log ล่าสุดที่ GitHub Actions เก็บไว้ลงเครื่อง
git pull

# ตรวจจำนวนแถวและช่องว่างข้อมูลแยกตามเหรียญ
.\.venv\Scripts\python.exe check_db.py

# ส่งออกไฟล์ CSV ไปที่โฟลเดอร์ exports\ สำหรับนำเข้า Power BI
.\.venv\Scripts\python.exe export_csv.py

# เปิดหน้าเว็บ Streamlit Dashboard (กด Ctrl+C ใน Terminal เพื่อปิด)
.\.venv\Scripts\streamlit.exe run dashboard.py
```

---

## 2. ดู Log และรัน Unit Tests

```powershell
# ดู log 10 บรรทัดล่าสุด (ใส่ -Encoding utf8 เพื่ออ่านภาษาไทยไม่เพี้ยน)
Get-Content pipeline.log -Tail 10 -Encoding utf8

# รัน Unit Tests ทั้งหมดด้วย pytest
.\.venv\Scripts\python.exe -m pytest -v

# เช็ค Exit Code ของคำสั่งล่าสุด (0 = สำเร็จ, 1 = ล้มเหลว)
$LASTEXITCODE
```

> **ข้อควรระวัง:** หากทดสอบรัน `.\.venv\Scripts\python.exe main.py` บนเครื่องตัวเอง อย่า `git add crypto.db` แล้ว push ทับข้อมูลจาก GitHub Actions

---

## 3. แก้โค้ดแล้วอัปขึ้น GitHub (Git Workflow)

```powershell
# เช็คไฟล์ที่ถูกแก้ไข
git status

# เลือกเฉพาะไฟล์โค้ดที่ต้องการอัปขึ้น
git add <ชื่อไฟล์ที่แก้>

# บันทึก commit
git commit -m "อธิบายสิ่งที่แก้"

# สำคัญ! ดึงข้อมูลล่าสุดจาก GitHub Actions ลงมาก่อน push เสมอ
git pull --rebase

# อัปขึ้น GitHub (จะทริกเกอร์ pytest CI อัตโนมัติ)
git push
```

---

## 4. จัดการ Virtual Environment (`.venv`)

```powershell
# ดูแพ็กเกจทั้งหมดที่ติดตั้งใน .venv
.\.venv\Scripts\python.exe -m pip list

# ติดตั้งแพ็กเกจทั้งหมดจาก requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 5. Windows Task Scheduler (`CryptoPrice`)

*(ปัจจุบันปิดเป็น `Disabled` เพราะย้ายไปรัน 24/7 บน GitHub Actions แล้ว)*

```powershell
# เช็คสถานะงาน
schtasks /query /tn "CryptoPrice" /v /fo list

# ปิดชั่วคราว
schtasks /change /tn "CryptoPrice" /disable

# เปิดกลับมาทำงานบนเครื่อง
schtasks /change /tn "CryptoPrice" /enable

# ลบงานถาวร
schtasks /delete /tn "CryptoPrice" /f
```

---

## 6. ทดสอบยิง Discord Webhook

```powershell
Invoke-RestMethod -Uri "URL_WEBHOOK_ของคุณ" -Method Post -ContentType "application/json" -Body '{"content":"✅ Test Discord Webhook"}'
```
