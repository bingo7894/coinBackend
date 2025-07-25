# Dockerfile
# เลือก Python base image ที่เหมาะสม
# ใช้เวอร์ชันที่แน่นอนและเป็น 'slim' เพื่อลดขนาดและเวลาโหลด
FROM python:3.11-slim-buster

# กำหนด Working Directory ภายใน Docker image
WORKDIR /app

# ขั้นตอนสำคัญสำหรับ Build Caching:
# 1. คัดลอกเฉพาะ requirements.txt มาก่อน
#    ถ้าไฟล์นี้ไม่เปลี่ยนแปลง Docker จะนำ Layer นี้มาใช้ใหม่ (ไม่ต้องติดตั้ง pip ใหม่)
COPY requirements.txt .

# 2. ติดตั้ง Python dependencies ทั้งหมด
#    --no-cache-dir ช่วยลดขนาด image สุดท้าย
#    --upgrade pip เพื่อให้แน่ใจว่า pip เป็นเวอร์ชันล่าสุด
#    และเพิ่มคำสั่งลบ cache ของ pip และ apt เพื่อลดขนาด image
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # ลบ cache ของ pip หลังจากติดตั้งเสร็จ
    rm -rf /root/.cache/pip && \
    # สำหรับ Debian/Ubuntu based images (slim-buster)
    # ลบ cache ของ apt และรายการแพ็คเกจที่ดาวน์โหลดมา
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. คัดลอกโค้ดแอปพลิเคชันที่เหลือทั้งหมด
#    ขั้นตอนนี้จะถูกรันใหม่ก็ต่อเมื่อโค้ดแอปพลิเคชันมีการเปลี่ยนแปลง
COPY . .

# กำหนด Environment Variable สำหรับ PORT หากจำเป็น (Railway จะให้มาอยู่แล้ว)
ENV PORT=$PORT

# ระบุ Command ที่จะรันเมื่อ Container เริ่มต้น (จาก Procfile เดิมของคุณ)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "$PORT"]

# หากมี Procfile ในโปรเจกต์ Railway จะตรวจพบและอาจใช้แทน CMD
# แต่การใส่ CMD ใน Dockerfile ก็ช่วยให้ Deploy ได้ในสภาพแวดล้อมอื่นๆ ด้วย
