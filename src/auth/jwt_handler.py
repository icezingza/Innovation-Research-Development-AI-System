import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


class InvalidTokenError(Exception):
    pass


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    secret: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise InvalidTokenError("Invalid or expired token") from exc
