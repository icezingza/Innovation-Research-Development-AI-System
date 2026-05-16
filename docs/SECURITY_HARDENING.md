# 🔐 IRD-AI Security Hardening Checklist

คู่มือการตั้งค่าระบบเพื่อความปลอดภัยระดับ Enterprise ก่อนนำขึ้น Production

---

## 1. Credential Management (สำคัญที่สุด)
- [ ] **เปลี่ยน Default Password:** อัปเดต `.env` ทั้งหมด (DB_PASSWORD, REDIS_PASSWORD, NEO4J_PASSWORD, JWT_SECRET_KEY) ด้วยรหัสผ่านที่สุ่มและมีความยาวไม่น้อยกว่า 32 ตัวอักษร
- [ ] **Admin Account:** ตรวจสอบและเปลี่ยนรหัสผ่านเริ่มต้นของ Admin Tenant ที่ตั้งค่าผ่าน `scripts/init_admin.sh` ทันทีหลังจาก Login ครั้งแรก

## 2. Infrastructure Hardening
- [ ] **Firewall Setup:** ปิด Port ทุกอย่างที่ไม่ได้ใช้งาน เปิดเฉพาะพอร์ตที่จำเป็น เช่น 8000 สำหรับ API (จำกัด Access จาก IP ภายในเท่านั้น)
- [ ] **Localhost Binding:** ตรวจสอบ `docker-compose.airgap.yml` ให้มั่นใจว่า Service Databases (5432, 6379, ฯลฯ) ถูก Bind เฉพาะ `127.0.0.1` เท่านั้น
- [ ] **System Security:** เปิดใช้งาน **AppArmor** หรือ **SELinux** เพื่อจำกัดสิทธิ์ของ Container ภายใน Host OS

## 3. Audit & Compliance
- [ ] **Audit Logging:** เปิดใช้งานระบบเก็บ Log อย่างเป็นทางการ และทำ Log Rotation ให้เรียบร้อย
- [ ] **Backups:** ตั้งค่า Cron Job เพื่อสำรองข้อมูลสำคัญ (PostgreSQL, Redis, Neo4j, Ollama Models) ไปยัง `/var/backups/ird-ai/` และตรวจสอบว่า Backup ถูกเข้ารหัส
- [ ] **Regulatory Guardrail Customization:** ตรวจสอบไฟล์ใน `src/security/rules/` ให้เหมาะสมกับนโยบายขององค์กร (เพิ่ม/ลด Keyword หรือ Pattern ตามความเสี่ยงของธุรกิจ)

## 4. Operational Hygiene
- [ ] **Container Security:** ทำการสแกน Image (เช่นด้วย Trivy) ก่อน Deploy ในสภาพแวดล้อมจริง
- [ ] **Network Isolation:** หากเป็นไปได้ ให้แยกส่วน Network ของ Application และ Database ออกจากกันโดยสมบูรณ์

---
*Stay Sovereign, Stay Secure.*
