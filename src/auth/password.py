from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt with 12 rounds.

    Args:
        plain: plaintext password string

    Returns:
        hashed password string (bcrypt format)
    """
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain: plaintext password to verify
        hashed: bcrypt hash to check against

    Returns:
        True if password matches hash, False otherwise
    """
    return _pwd_context.verify(plain, hashed)
