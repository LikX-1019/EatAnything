from starlette.requests import Request

from app.core import rate_limit
from app.core.rate_limit import RateLimiter


def request(path: str, method: str = "POST", host: str = "10.0.0.8", headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request({
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "client": (host, 1234),
        "server": ("test", 80),
        "scheme": "http",
    })


class Settings:
    trusted_proxy_ips = "10.0.0.8"


def test_login_rate_limit_is_applied_per_client() -> None:
    limiter = RateLimiter()
    settings = Settings()
    for _ in range(20):
        assert limiter.check(request("/api/v1/admin/auth/login"), settings) is None
    retry_after = limiter.check(request("/api/v1/admin/auth/login"), settings)
    assert retry_after is not None and retry_after > 0


def test_forwarded_for_is_used_only_from_trusted_proxy() -> None:
    limiter = RateLimiter()
    settings = Settings()
    trusted = request("/api/v1/auth/dev-login", host="10.0.0.8", headers=[(b"x-forwarded-for", b"192.0.2.10")])
    untrusted = request("/api/v1/auth/dev-login", host="10.0.0.9", headers=[(b"x-forwarded-for", b"192.0.2.10")])
    assert limiter.client_ip(trusted, settings) == "192.0.2.10"
    assert limiter.client_ip(untrusted, settings) == "10.0.0.9"


def test_draw_rate_limit_is_isolated_by_bearer_token_behind_proxy() -> None:
    limiter = RateLimiter()
    settings = Settings()
    first_headers = [(b"authorization", b"Bearer user-token-1")]
    second_headers = [(b"authorization", b"Bearer user-token-2")]

    for _ in range(5):
        assert limiter.check(request("/api/v1/stores/random", headers=first_headers), settings) is None

    assert limiter.check(request("/api/v1/stores/random", headers=first_headers), settings) is not None
    assert limiter.check(request("/api/v1/stores/random", headers=second_headers), settings) is None


def test_authenticated_write_limit_does_not_store_raw_token() -> None:
    limiter = RateLimiter()
    settings = Settings()
    raw_token = "sensitive-user-token"

    assert limiter.check(
        request("/api/v1/me/favorites/1", method="PUT", headers=[(b"authorization", f"Bearer {raw_token}".encode())]),
        settings,
    ) is None

    assert all(raw_token not in key_part for key in limiter._events for key_part in key)


def test_rate_limit_removes_inactive_token_keys(monkeypatch) -> None:
    limiter = RateLimiter()
    settings = Settings()
    limiter._events[("token:stale", "draw")].append(0.0)
    limiter._last_cleanup_at = 0.0
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: 61.0)

    assert limiter.check(
        request("/api/v1/stores/random", headers=[(b"authorization", b"Bearer current-token")]),
        settings,
    ) is None

    assert ("token:stale", "draw") not in limiter._events
