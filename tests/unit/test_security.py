from __future__ import annotations

from bemestar.infrastructure.security import (
    create_session,
    hash_password,
    verify_password,
    verify_session,
)


def test_password_roundtrip() -> None:
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_session_roundtrip() -> None:
    token, csrf = create_session("owner", "a-strong-secret", 60)
    payload = verify_session(token, "a-strong-secret")
    assert payload is not None
    assert payload["sub"] == "owner"
    assert payload["csrf"] == csrf
    assert verify_session(token, "wrong-secret") is None


def test_rate_limiter_has_bounded_key_cardinality() -> None:
    from bemestar.infrastructure.security import MemoryRateLimiter, RateRule

    limiter = MemoryRateLimiter(max_keys=100)
    rule = RateRule(limit=10, window_seconds=60)
    for idx in range(250):
        assert limiter.allow(f"ip:{idx}", rule)
    assert limiter.key_count == 100
