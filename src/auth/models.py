from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    org_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    tenant: TenantOut


class MeResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
    role: str
