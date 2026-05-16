from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from src.api.dependencies import get_db
from src.security.auth_utils import verify_password, create_access_token, decode_token
from datetime import timedelta
import uuid

# สมมติโมเดล User และ Tenant ถูกนิยามไว้ใน src/models/...
# ในที่นี้จะขอใช้การ query ตรงผ่าน sqlalchemy
from src.memory.schema import User, Tenant

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. ตรวจสอบ Tenant
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == req.tenant_id, Tenant.status == 'active'))
    tenant = tenant_res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inactive or not found")

    # 2. ตรวจสอบ User ใน Tenant นั้น
    user_res = await db.execute(select(User).where(User.email == req.email, User.tenant_id == req.tenant_id))
    user = user_res.scalars().first()
    
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3. สร้าง Token
    access_token = create_access_token(data={"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role})
    # refresh_token เก็บลง DB/Redis (ในอนาคต)
    
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        # ฝังลงใน request state เพื่อให้ Middleware/Route ดึงไปใช้ต่อ
        request.state.tenant_id = payload.get("tenant_id")
        request.state.user_id = payload.get("sub")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
