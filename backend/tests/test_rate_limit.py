from starlette.requests import Request

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
