# 📸 Pitch Deck Screenshot Capture Guide
**NamoNexus Phase 4 — 6 Moats Demo**
Audience priority: **B (Business)** → A (Technical) → C (Security)

## ✅ Live Demo Session Active

| Field | Value |
|---|---|
| 🟢 Server | `http://127.0.0.1:8012` |
| 🏢 Tenant A (Acme, Pro) | `b6ea7201-bd70-464f-afb6-ffde18d62484` |
| 🏢 Tenant B (Beta, Free) | `3a1817eb-9670-463e-abfa-2a200b74afde` |
| 🔬 Task ID | `9baba5ac-47b0-4a39-b59a-4bd476cc5c08` |
| 🔐 Password | `Pass1234!` |

### JWT Token A (Acme — for capture)
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MmYwZWI4My1jNzJjLTQ2ODQtOTJhNi0wNmJjZWYzMDg5YzYiLCJ0ZW5hbnRfaWQiOiJiNmVhNzIwMS1iZDcwLTQ2NGYtYWZiNi1mZmRlMThkNjI0ODQiLCJyb2xlIjoib3duZXIiLCJleHAiOjE3Nzg5MjY2MzR9.dN7nEIEg57Mwyfl08AeMnkwGQg70WZJ0cXnAeZsajsI
```

### JWT Token B (Beta — for isolation proof only)
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NjAwZTQ3My1hMGQzLTQxZjMtOTlkNi1mNjFiZmQ5Mzc1MDAiLCJ0ZW5hbnRfaWQiOiIzYTE4MTdlYi05NjcwLTQ2M2UtYWJmYS0yYTIwMGI3NGFmZGUiLCJyb2xlIjoib3duZXIiLCJleHAiOjE3Nzg5MjY2MzR9.rIClPmzrqymcK69r3itZyMjcR_HHvQ5BrGJb3VHTIhQ
```

---

## 📋 Screenshot Sequence (5 shots → Pitch Deck slides 8-12)

### 🖼️ Shot 1 — FinOps Dashboard (Slide 8: "Cognitive FinOps")
**Selling point:** *CFO sees AI cost + budget forecast in 3 seconds*

**ขั้นตอน:**
1. เปิด Chrome/Edge → URL:
   ```
   http://127.0.0.1:8012/dashboard/finops/b6ea7201-bd70-464f-afb6-ffde18d62484
   ```
2. กด **F12** → tab **Console** → paste:
   ```js
   localStorage.setItem('token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MmYwZWI4My1jNzJjLTQ2ODQtOTJhNi0wNmJjZWYzMDg5YzYiLCJ0ZW5hbnRfaWQiOiJiNmVhNzIwMS1iZDcwLTQ2NGYtYWZiNi1mZmRlMThkNjI0ODQiLCJyb2xlIjoib3duZXIiLCJleHAiOjE3Nzg5MjY2MzR9.dN7nEIEg57Mwyfl08AeMnkwGQg70WZJ0cXnAeZsajsI');
   location.reload();
   ```
3. รอ chart โหลด → **Win+Shift+S** → save `pitch_01_finops.png`

---

### 🖼️ Shot 2 — ROI Dashboard (Slide 9: "Quantified Business Value")
**Selling point:** *60-80% savings vs cloud AI (Bedrock/Vertex)*

**ขั้นตอน:**
1. URL: `http://127.0.0.1:8012/dashboard/roi`
2. (Token from Shot 1 still in localStorage)
3. **Win+Shift+S** → `pitch_02_roi.png`

---

### 🖼️ Shot 3 — Audit Trail Timeline (Slide 10: "Auditable AI")
**Selling point:** *Every AI decision auditable — Hypothesis → Critique → Synthesis*

**ขั้นตอน:**
1. URL:
   ```
   http://127.0.0.1:8012/dashboard/trace/9baba5ac-47b0-4a39-b59a-4bd476cc5c08
   ```
2. **Win+Shift+S** → `pitch_03_audit_trail.png`

> 💡 ถ้า timeline ว่าง: รัน `python` script ด้านล่างเพื่อ trigger agents:

```python
import requests
TOKEN_A = "<paste token A>"
TASK_ID = "9baba5ac-47b0-4a39-b59a-4bd476cc5c08"
# Force trace populate by hitting trace endpoint multiple times
for _ in range(3):
    requests.get(f"http://127.0.0.1:8012/research/tasks/{TASK_ID}/trace",
                 headers={"Authorization": f"Bearer {TOKEN_A}"})
```

---

### 🖼️ Shot 4 — Swagger UI / API Coverage (Slide 11: "Production-Grade API")
**Selling point:** *OpenAPI 3.0 spec, every endpoint documented & JWT-protected*

**ขั้นตอน:**
1. URL: `http://127.0.0.1:8012/docs`
2. คลิก **Authorize** (มุมบนขวา) → ใส่:
   ```
   Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3MmYwZWI4My1jNzJjLTQ2ODQtOTJhNi0wNmJjZWYzMDg5YzYi...
   ```
3. Scroll → **GET /research/tasks/{task_id}/trace**
4. คลิก **Try it out** → `task_id`: `9baba5ac-47b0-4a39-b59a-4bd476cc5c08` → **Execute**
5. **Win+Shift+S** capture request + JSON response → `pitch_04_api_docs.png`

---

### 🖼️ Shot 5 — Security Isolation Proof (Slide 12: "Multi-Tenant Security")
**Selling point:** *Tenant B cannot access Tenant A's financial data — proven*

เปิด **PowerShell** แล้ว paste:

```powershell
$tokenB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NjAwZTQ3My1hMGQzLTQxZjMtOTlkNi1mNjFiZmQ5Mzc1MDAiLCJ0ZW5hbnRfaWQiOiIzYTE4MTdlYi05NjcwLTQ2M2UtYWJmYS0yYTIwMGI3NGFmZGUiLCJyb2xlIjoib3duZXIiLCJleHAiOjE3Nzg5MjY2MzR9.rIClPmzrqymcK69r3itZyMjcR_HHvQ5BrGJb3VHTIhQ"
curl.exe -i -H "Authorization: Bearer $tokenB" "http://127.0.0.1:8012/tenants/b6ea7201-bd70-464f-afb6-ffde18d62484/finops"
```

**Expected output:**
```
HTTP/1.1 403 Forbidden
content-type: application/json
{"detail":"Access denied"}
```

**Win+Shift+S** capture terminal → `pitch_05_isolation_proof.png`

---

## 🗂️ Save Files Layout
```
demo_artifacts/
├── demo_session.json          (auto-generated)
├── SCREENSHOT_GUIDE.md        (this file)
└── screenshots/
    ├── pitch_01_finops.png
    ├── pitch_02_roi.png
    ├── pitch_03_audit_trail.png
    ├── pitch_04_api_docs.png
    └── pitch_05_isolation_proof.png
```

---

## 📊 Pitch Deck Slide Mapping
| Slide # | Screenshot | Title Suggestion | Sub-text |
|---|---|---|---|
| 8 | `pitch_01_finops.png` | **Cognitive FinOps** | "Real-time AI cost visibility — CFO dashboard" |
| 9 | `pitch_02_roi.png` | **Quantified ROI** | "60-80% cost savings vs cloud AI services" |
| 10 | `pitch_03_audit_trail.png` | **Auditable AI** | "Every decision traced — regulatory-ready" |
| 11 | `pitch_04_api_docs.png` | **Production API** | "OpenAPI 3.0, JWT-secured, fully documented" |
| 12 | `pitch_05_isolation_proof.png` | **Multi-Tenant Security** | "Enterprise-grade isolation — proven by test" |

---

## ⚠️ ถ้า Server หยุดทำงาน

```bash
cd "C:\Users\icezi\Downloads\Github repo\Innovation-Research-Development-AI-System-main\Innovation-Research-Development-AI-System-main"
python -m uvicorn src.api.main:app --port 8012
```

แล้วรัน `python demo_pitch_deck.py` เพื่อสร้าง session ใหม่
(JWT จะใหม่หมด — copy จาก `demo_artifacts/demo_session.json`)

---

## 🔐 Security Follow-up (ก่อน demo จริง)
- [ ] Revoke DeepSeek key `sk-fa5d0cc923...` → generate new
- [ ] Revoke OpenRouter key `sk-or-v1-c74863803...` → generate new
- [ ] อัพเดต `.env` ด้วย key ใหม่ (อย่า commit)
