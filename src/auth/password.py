from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using argon2.

    Args:
        plain: plaintext password string

    Returns:
        hashed password string (argon2 format)
    """
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2 hash.

    Args:
        plain: plaintext password to verify
        hashed: argon2 hash to check against

    Returns:
        True if password matches hash, False otherwise
    """
    return _pwd_context.verify(plain, hashed)
