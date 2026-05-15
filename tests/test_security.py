
from src.security.api_keys import APIKeyManager
from src.security.rate_limiter import RateLimiter


# ---------- APIKeyManager ----------

def test_api_key_manager_disabled_when_empty():
    mgr = APIKeyManager(raw_keys="")
    assert mgr.enabled is False
    assert mgr.validate(None) is True
    assert mgr.validate("anything") is True


def test_api_key_manager_validates_correct_key():
    mgr = APIKeyManager(raw_keys="secret-key-1,secret-key-2")
    assert mgr.enabled is True
    assert mgr.validate("secret-key-1") is True
    assert mgr.validate("secret-key-2") is True


def test_api_key_manager_rejects_wrong_key():
    mgr = APIKeyManager(raw_keys="correct-key")
    assert mgr.validate("wrong-key") is False


def test_api_key_manager_rejects_none_when_enabled():
    mgr = APIKeyManager(raw_keys="key-abc")
    assert mgr.validate(None) is False


def test_api_key_manager_trims_whitespace():
    mgr = APIKeyManager(raw_keys="  key-a  ,  key-b  ")
    assert mgr.validate("key-a") is True
    assert mgr.validate("key-b") is True


def test_api_key_generate_produces_unique_keys():
    k1 = APIKeyManager.generate_key()
    k2 = APIKeyManager.generate_key()
    assert k1 != k2
    assert len(k1) >= 32


# ---------- RateLimiter ----------

def test_rate_limiter_disabled_always_allows():
    rl = RateLimiter(requests_per_minute=1, enabled=False)
    for _ in range(100):
        assert rl.is_allowed("client") is True


def test_rate_limiter_allows_within_limit():
    rl = RateLimiter(requests_per_minute=5, enabled=True)
    for _ in range(5):
        assert rl.is_allowed("client-a") is True


def test_rate_limiter_blocks_over_limit():
    rl = RateLimiter(requests_per_minute=3, enabled=True)
    for _ in range(3):
        rl.is_allowed("client-b")
    assert rl.is_allowed("client-b") is False


def test_rate_limiter_isolates_clients():
    rl = RateLimiter(requests_per_minute=2, enabled=True)
    rl.is_allowed("client-x")
    rl.is_allowed("client-x")
    assert rl.is_allowed("client-x") is False
    assert rl.is_allowed("client-y") is True


def test_rate_limiter_current_count():
    rl = RateLimiter(requests_per_minute=10, enabled=True)
    rl.is_allowed("c")
    rl.is_allowed("c")
    assert rl.current_count("c") == 2
