"""应用层基础限流。

这是单 worker 内存限流；同一容器内的多个 Uvicorn worker 和多个 API 副本
都会独立计数。需要全局限流时应迁移到 Redis 等共享存储，并保持相同限额。
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import Settings


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._last_cleanup_at = 0.0

    def check(self, request: Request, settings: Settings) -> int | None:
        rule = self._rule(request)
        if rule is None:
            return None
        limit, window = rule
        bucket = self.bucket(request)
        key = (self.client_key(request, settings, bucket), bucket)
        now = time.monotonic()
        self._cleanup_stale_keys(now)
        events = self._events[key]
        while events and events[0] <= now - window:
            events.popleft()
        if len(events) >= limit:
            return max(1, int(window - (now - events[0])))
        events.append(now)
        return None

    def _cleanup_stale_keys(self, now: float) -> None:
        if now - self._last_cleanup_at < 60:
            return
        self._last_cleanup_at = now
        stale_before = now - 60
        stale_keys = [key for key, events in self._events.items() if not events or events[-1] <= stale_before]
        for key in stale_keys:
            self._events.pop(key, None)

    @staticmethod
    def client_ip(request: Request, settings: Settings) -> str:
        peer = request.client.host if request.client else "unknown"
        trusted = {item.strip() for item in settings.trusted_proxy_ips.split(",") if item.strip()}
        if peer in trusted:
            forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded
        return peer

    @classmethod
    def client_key(cls, request: Request, settings: Settings, bucket: str) -> str:
        """为已认证写请求使用 Token 指纹，避免反向代理后的用户共享同一限额。"""
        if bucket in {"draw", "upload", "write"}:
            scheme, _, credentials = request.headers.get("Authorization", "").partition(" ")
            token = credentials.strip()
            if scheme.lower() == "bearer" and token:
                digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
                return f"token:{digest}"
        return f"ip:{cls.client_ip(request, settings)}"

    @staticmethod
    def bucket(request: Request) -> str:
        path = request.url.path
        if path in {"/api/v1/auth/wechat-login", "/api/v1/auth/dev-login", "/api/v1/admin/auth/login"}:
            return "login"
        if path == "/api/v1/stores/random":
            return "draw"
        if path.endswith("/import") or "/uploads/" in path:
            return "upload"
        return "write"

    @staticmethod
    def _rule(request: Request) -> tuple[int, int] | None:
        path = request.url.path
        if request.method == "POST" and path in {"/api/v1/auth/wechat-login", "/api/v1/auth/dev-login", "/api/v1/admin/auth/login"}:
            return (20, 60)
        if request.method == "POST" and path == "/api/v1/stores/random":
            return (5, 1)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (path.endswith("/import") or "/uploads/" in path):
            return (30, 60)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and path.startswith("/api/v1/"):
            return (120, 60)
        return None


rate_limiter = RateLimiter()
