# 🔒 IRD-AI Air-Gapped Deployment Guide

คู่มือการติดตั้งสำหรับ **องค์กรที่ต้องการรันระบบในห้องปิด (Air-Gapped)**  
ไม่มีการเชื่อมต่ออินเทอร์เน็ตใด ๆ ทั้งสิ้น  

---

## 📋 Requirements
- Docker 24+ และ Docker Compose v2+ (ติดตั้งจากไฟล์ Offline)
- Kubernetes 1.28+ (สำหรับ Helm Deployment)
- RAM: อย่างน้อย 32 GB (แนะนำ 64 GB สำหรับ Ollama)
- Storage: SSD อย่างน้อย 200 GB
- OS: Ubuntu 22.04 LTS หรือ RHEL 9

---

## 🚀 Quick Start — Docker Compose

### 1. โอนไฟล์ทั้งหมดเข้าเครื่องเป้าหมาย
```bash
# ผ่าน External Drive หรือ Internal File Server
cp -r /media/usb/ird-ai-deploy /opt/ird-ai
cd /opt/ird-ai
```

### 2. กำหนดค่าสภาพแวดล้อม
สร้างไฟล์ `.env` โดยอิงจากตัวอย่าง:
```bash
cp .env.example .env
# แก้ไขรหัสผ่านและค่าติดตั้งใน .env ให้เรียบร้อย
```

### 3. เริ่มรันระบบ
```bash
docker compose -f docker-compose.airgap.yml up -d
```

---

## ☸️ Quick Start — Kubernetes (Helm)

### 1. โอนไฟล์ Helm Chart เข้าเครื่องเป้าหมาย
```bash
# คัดลอกโฟลเดอร์ helm/ird-ai/ ไปยังเครื่องเป้าหมาย
scp -r ./helm/ird-ai/ user@target-node:/home/user/deploy/
```

### 2. เตรียม Image ใน Private Registry
เนื่องจากเป็น Air-Gapped ต้อง Push images ไปที่ Internal Registry ก่อน:
```bash
# พอร์ตการทำ Offline Image Export/Import
docker save ird-ai/app:0.9.0 > ird-app.tar
# ...นำไฟล์ .tar ไป Load ที่เครื่องเป้าหมาย
docker load < ird-app.tar
```

### 3. Deploy ผ่าน Helm
```bash
helm install ird-ai ./ird-ai -f ./ird-ai/values.yaml
```

---

## 🤖 Ollama Setup (Air-Gapped)
1. **Pull Model ในเครื่องที่ต่อเน็ต:**
   ```bash
   ollama pull llama3
   ```
2. **Export Model:**
   ```bash
   # สำรองโฟลเดอร์ /var/lib/ollama ไปยังเครื่องเป้าหมาย
   ```
3. **Load Model:**
   วางไฟล์ใน Volume ของ Ollama ที่กำหนดไว้ใน `docker-compose.airgap.yml`

---
*Confidential – IRD-AI All Rights Reserved.*
