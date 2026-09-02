# 💊 PharmaCU Flashcard Private — Web App

ระบบ Flashcard ทบทวนข้อสอบและเภสัชวิทยาความเร็วสูง รองรับการใช้งานแบบ Offline 100% (PWA) และ Deploy ผ่าน **GitHub Pages** (ไม่ต้องใช้ Vercel และไม่หน่วงเหมือน Google Apps Script)

---

## ⚡ ทำไมระบบนี้ถึงเร็วกว่าเดิมมาก?
1. **0.1s Instant Load:** ข้อมูลการ์ดทั้ง 639 ข้อ (Tab 8: 105 ข้อ, Tab 16: 285 ข้อ, Tab อื่นๆ 249 ข้อ) ถูกคอมไพล์ลงใน `flashcard-data-offline.js` แล้ว ไม่ต้องรอ Google Apps Script บูตเครื่อง
2. **Offline 100% (PWA):** รองรับ Service Worker สามารถกด "Add to Home Screen" บน iPad/iPhone เปิดอ่านได้แม้ไม่มีสัญญาณอินเทอร์เน็ต
3. **Local Progress Persistence:** บันทึกข้อที่ "จำได้แล้ว" หรือ "ยังไม่แม่น" ลงใน LocalStorage ของเครื่องทันที ไม่มีดีเลย์

---

## 🚀 ขั้นตอนการใช้งานประจำวัน

### 1. อัปเดตข้อมูลจากการแก้ใน Google Sheet
เมื่อคุณแก้ไขหรือเพิ่มข้อสอบใน Google Sheet ส่วนตัว (`Flashcard CC1 Private`):
- ดับเบิลคลิกไฟล์ **`compile_offline_db.bat`**
- ระบบจะดึงข้อมูลสด แปลงสีและรูปแบบ RichText แล้วบันทึกลง `flashcard-data-offline.js` อัตโนมัติใน ~5 วินาที

### 2. ทดลองเปิดดูในเครื่องทันที
- ดับเบิลคลิกเปิดไฟล์ **`index.html`** ด้วย Chrome / Edge / Safari ได้ทันที

### 3. นำขึ้น GitHub Pages (เพื่อเปิดอ่านบนมือถือ/iPad ได้ทุกที่)
1. สร้าง New Repository บน GitHub (เช่น ชื่อ `PharmaCU-Flashcard-Private`)
2. ในโฟลเดอร์นี้ เปิด PowerShell / Terminal แล้วรันคำสั่งเชื่อมต่อครั้งแรก:
   ```bash
   git init
   git branch -M main
   git remote add origin https://github.com/<username>/<repo-name>.git
   ```
3. ต่อไปเมื่อต้องการอัปเดตขึ้นเว็บ:
   - ดับเบิลคลิกไฟล์ **`🚀 Push to GitHub.bat`** ได้เลย!
4. ไปที่ GitHub Repo -> **Settings** -> **Pages** -> เลือก **Deploy from a branch (main / root)**
5. เว็บจะพร้อมใช้งานที่: `https://<username>.github.io/<repo-name>/` ทันที!

---

## ⌨️ ปุ่มลัดบนคีย์บอร์ด (Keyboard Shortcuts)
- **`Space` หรือ `Enter`**: พลิกการ์ด (Flip Card)
- **`←` / `→` (หรือ `J` / `L`)**: ข้อก่อนหน้า / ข้อถัดไป
- **`1`**: บันทึกว่า "⚠️ ยังไม่แม่น" (ต้องทวน)
- **`2`**: บันทึกว่า "✅ จำได้แล้ว" (Mastered)
- **`S`**: ติดดาวข้อสอบ (Bookmark / Star)
