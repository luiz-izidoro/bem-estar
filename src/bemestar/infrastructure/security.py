from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections import OrderedDict, deque
from dataclasses import dataclass


def hash_password(password: str, iterations: int = 600_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_s, salt_s, digest_s = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_s.encode())
        expected = base64.urlsafe_b64decode(digest_s.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations_s))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_session(username: str, secret: str, ttl_seconds: int) -> tuple[str, str]:
    now = int(time.time())
    csrf = _b64(os.urandom(24))
    payload = {"sub": username, "iat": now, "exp": now + ttl_seconds, "csrf": csrf}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", csrf


def verify_session(token: str, secret: str) -> dict[str, object] | None:
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body))
        if not isinstance(payload, dict):
            return None
        data: dict[str, object] = payload
        if int(str(data.get("exp", 0))) < int(time.time()):
            return None
        return data
    except (ValueError, KeyError, json.JSONDecodeError, TypeError):
        return None


@dataclass(slots=True, frozen=True)
class RateRule:
    limit: int
    window_seconds: int


class MemoryRateLimiter:
    """Small bounded single-process limiter for brute-force/abuse mitigation.

    It intentionally is *not* volumetric DDoS protection. Caddy and, when needed,
    an upstream provider remain the network edge. The LRU bound prevents arbitrary
    source addresses from growing process memory without limit.
    """

    def __init__(self, max_keys: int = 10_000) -> None:
        if max_keys < 100:
            raise ValueError("max_keys must be >= 100")
        self.max_keys = max_keys
        self._events: OrderedDict[str, deque[float]] = OrderedDict()

    def allow(self, key: str, rule: RateRule) -> bool:
        now = time.monotonic()
        q = self._events.get(key)
        if q is None:
            if len(self._events) >= self.max_keys:
                self._events.popitem(last=False)
            q = deque()
            self._events[key] = q
        else:
            self._events.move_to_end(key)

        cutoff = now - rule.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= rule.limit:
            return False
        q.append(now)
        return True

    @property
    def key_count(self) -> int:
        return len(self._events)
