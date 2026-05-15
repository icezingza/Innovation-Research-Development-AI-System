# Phase 3B Design Spec — Auth & API Gateway (JWT)

**Date:** 2026-05-16  
**Author:** Namo (AI Project Leader)  
**Status:** Approved  
**Depends on:** Phase 3A (Multi-tenant schema)

---

## 1. Objective

Replace the static X-API-Key system with full JWT-based authentication. Users log in and receive tokens scoped to their tenant. All protected endpoints verify the JWT and inject `TenantContext` into the request.

**Success criterion:** An unauthenticated request to any endpoint (except /health, /metrics, /auth/*) returns 401. A valid JWT unlocks the full API scoped to the caller's tenant.

---

## 2. Token Strategy

| Token | Lifetime | Storage | Purpose |
|---|---|---|---|
| Access Token (JWT) | 15 minutes | Authorization header | API access |
| Refresh Token (opaque) | 7 days | httpOnly cookie | Renew access token |

- Algorithm: **HS256** (symmetric, simple, sufficient for single-service)
- Secret: `JWT_SECRET` env var (min 32 chars)
- Refresh tokens stored in Redis with TTL for revocation support

### JWT Payload
```json
{
  "sub": "<user_id>",
  "tenant_id": "<tenant_id>",
  "role": "owner | admin | member",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "<unique token id>"
}
```

---

## 3. New Auth Endpoints (`/auth`)

| Method | Path | Description | Auth required |
|---|---|---|---|
| POST | `/auth/register` | Create user + tenant | No |
| POST | `/auth/login` | Issue access + refresh token | No |
| POST | `/auth/refresh` | Renew access token via cookie | No (uses cookie) |
| POST | `/auth/logout` | Revoke refresh token | Yes |
| GET | `/auth/me` | Current user + tenant info | Yes |

---

## 4. Registration Flow

```
POST /auth/register
Body: { email, password, display_name, org_name }

1. Validate email uniqueness
2. Hash password (bcrypt, cost=12)
3. Create User record
4. Create Tenant record (slug = slugify(org_name))
5. Create TenantMember (role=owner)
6. Issue access token + refresh token
7. Return: { access_token, user, tenant }
```

---

## 5. Login Flow

```
POST /auth/login
Body: { email, password }

1. Look up user by email
2. Verify password (bcrypt)
3. Update last_login_at
4. Issue JWT access token (15 min)
5. Issue refresh token → store in Redis (key: refresh:<jti>, value: user_id, TTL: 7d)
6. Set refresh token in httpOnly cookie
7. Return: { access_token, expires_in: 900, user }
```

---

## 6. JWT Middleware

Replaces `SecurityMiddleware` as the primary auth layer.

```
Exempt paths: /health, /metrics, /auth/*, /dashboard/*

For all other paths:
1. Extract Bearer token from Authorization header
2. Decode + verify JWT (HS256, check exp)
3. Load TenantContext from JWT payload
4. Set request.state.tenant = TenantContext(tenant_id, user_id, role)
5. On failure: 401 Unauthorized

X-API-Key header still accepted for machine-to-machine (service accounts)
```

---

## 7. File Structure

```
src/
├── auth/
│   ├── jwt_handler.py      ← encode/decode JWT, token creation
│   ├── password.py         ← bcrypt hash/verify
│   ├── refresh_store.py    ← Redis refresh token storage
│   └── models.py           ← Pydantic request/response schemas
├── api/
│   ├── middleware.py       ← extend with JWT verification
│   └── routes/
│       └── auth.py         ← /auth/* endpoints
```

---

## 8. Role-Based Access Control (RBAC)

Simple decorator-based guards:

```python
# Usage on route handlers
@require_role("admin", "owner")
async def delete_workflow(request: Request): ...
```

- `owner` — full access including tenant management
- `admin` — full access to research operations
- `member` — read + create workflows, cannot delete

---

## 9. Security Checklist

- [x] Passwords hashed with bcrypt cost=12
- [x] JWT secret minimum 32 chars enforced at startup
- [x] Refresh tokens revocable via Redis delete
- [x] Access tokens short-lived (15 min)
- [x] httpOnly cookie for refresh token (XSS protection)
- [x] No sensitive data in JWT payload (no password, no billing)
- [x] Constant-time comparison for refresh token lookup

---

## 10. Out of Scope (Phase 3B)

- OAuth2 / SSO (Phase 4)
- Email verification
- Password reset flow
- 2FA
