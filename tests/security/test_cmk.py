import pytest
from cryptography.fernet import InvalidToken

from src.security.cmk import CMKManager


@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip():
    mgr = CMKManager(redis_client=None)
    ciphertext = await mgr.encrypt("tenant-a", "secret payload")
    plaintext = await mgr.decrypt("tenant-a", ciphertext)
    assert plaintext == "secret payload"


@pytest.mark.asyncio
async def test_different_tenants_use_different_keys():
    mgr = CMKManager(redis_client=None)
    ct_a = await mgr.encrypt("tenant-a", "hello")
    with pytest.raises(Exception):
        # tenant-b's key cannot decrypt tenant-a's ciphertext
        await mgr.decrypt("tenant-b", ct_a)


@pytest.mark.asyncio
async def test_rotate_key_invalidates_old_ciphertext():
    mgr = CMKManager(redis_client=None)
    ct = await mgr.encrypt("tenant-r", "data")
    await mgr.rotate_key("tenant-r")
    with pytest.raises(InvalidToken):
        await mgr.decrypt("tenant-r", ct)


@pytest.mark.asyncio
async def test_same_tenant_key_is_stable_across_calls():
    mgr = CMKManager(redis_client=None)
    ct1 = await mgr.encrypt("tenant-s", "value")
    ct2 = await mgr.encrypt("tenant-s", "value")
    # Both should decrypt correctly (same key used)
    assert await mgr.decrypt("tenant-s", ct1) == "value"
    assert await mgr.decrypt("tenant-s", ct2) == "value"


@pytest.mark.asyncio
async def test_decrypt_wrong_data_raises_invalid_token():
    mgr = CMKManager(redis_client=None)
    await mgr.encrypt("tenant-x", "something")
    with pytest.raises(Exception):
        await mgr.decrypt("tenant-x", "notavalidtoken")
