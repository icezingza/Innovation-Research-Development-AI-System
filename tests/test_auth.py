import pytest
from datetime import timedelta
from unittest.mock import AsyncMock
from src.auth.password import hash_password, verify_password
from src.auth.jwt_handler import (
    create_access_token,
    decode_access_token,
    InvalidTokenError,
)
from src.auth.refresh_store import RefreshTokenStore

SECRET = "test-secret-that-is-at-least-32-characters-long"


class TestPassword:
    def test_hash_is_not_plaintext(self) -> None:
        h = hash_password("secret")
        assert h != "secret"

    def test_verify_correct_password(self) -> None:
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self) -> None:
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_hash_same_input_different_output(self) -> None:
        # hashing is salted — two hashes of same input must differ
        h1 = hash_password("secret")
        h2 = hash_password("secret")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_token(self) -> None:
        token = create_access_token("user1", "tenant1", "owner", SECRET)
        payload = decode_access_token(token, SECRET)
        assert payload["sub"] == "user1"
        assert payload["tenant_id"] == "tenant1"
        assert payload["role"] == "owner"

    def test_payload_has_jti(self) -> None:
        token = create_access_token("u", "t", "member", SECRET)
        payload = decode_access_token(token, SECRET)
        assert "jti" in payload

    def test_expired_token_raises(self) -> None:
        token = create_access_token(
            "u", "t", "member", SECRET, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(InvalidTokenError):
            decode_access_token(token, SECRET)

    def test_wrong_secret_raises(self) -> None:
        token = create_access_token("u", "t", "member", SECRET)
        with pytest.raises(InvalidTokenError):
            decode_access_token(token, "wrong-secret-that-is-at-least-32-chars-long")

    def test_tampered_token_raises(self) -> None:
        token = create_access_token("u", "t", "member", SECRET)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(InvalidTokenError):
            decode_access_token(tampered, SECRET)


@pytest.mark.asyncio
class TestRefreshTokenStore:
    async def test_create_returns_token_string(self) -> None:
        redis = AsyncMock()
        store = RefreshTokenStore(redis)
        token = await store.create("user1")
        assert isinstance(token, str)
        assert len(token) > 0
        redis.set.assert_awaited_once()

    async def test_get_user_id_returns_value(self) -> None:
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"user1")
        store = RefreshTokenStore(redis)
        user_id = await store.get_user_id("sometoken")
        assert user_id == "user1"

    async def test_get_user_id_returns_none_on_miss(self) -> None:
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        store = RefreshTokenStore(redis)
        result = await store.get_user_id("notoken")
        assert result is None

    async def test_revoke_deletes_key(self) -> None:
        redis = AsyncMock()
        store = RefreshTokenStore(redis)
        await store.revoke("mytoken")
        redis.delete.assert_awaited_once_with("refresh:mytoken")
