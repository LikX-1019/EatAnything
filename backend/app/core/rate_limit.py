"""应用层基础限流。

这是单实例内存限流，适合当前 Compose 单 API 容器部署；多副本部署时应将
同一算法迁移到 Redis 等共享存储，并在发布前保持相同限额。
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import Settings


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, request: Request, settings: Settings) -> int | None:
        rule = self._rule(request)
        if rule is None:
            return None
        limit, window = rule
        key = (self.client_ip(request, settings), self.bucket(request))
        now = time.monotonic()
        events = self._events[key]
        while events and events[0] <= now - window:
            events.popleft()
        if len(events) >= limit:
            return max(1, int(window - (now - events[0])))
        events.append(now)
        return None

    @staticmethod
    def client_ip(request: Request, settings: Settings) -> str:
        peer = request.client.host if request.client else "unknown"
        trusted = {item.strip() for item in settings.trusted_proxy_ips.split(",") if item.strip()}
        if peer in trusted:
            forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded
        return peer

    @staticmethod
    def bucket(request: Request) -> str:
        path = request.url.path
        if path in {"/api/v1/auth/wechat-login", "/api/v1/auth/dev-login", "/api/v1/admin/auth/login"}:
            return "login"
        if path.endswith("/import") or "/uploads/" in path:
            return "upload"
        return "write"

    @staticmethod
    def _rule(request: Request) -> tuple[int, int] | None:
        path = request.url.path
        if request.method == "POST" and path in {"/api/v1/auth/wechat-login", "/api/v1/auth/dev-login", "/api/v1/admin/auth/login"}:
            return (20, 60)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (path.endswith("/import") or "/uploads/" in path):
            return (30, 60)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and path.startswith("/api/v1/"):
            return (120, 60)
        return None


rate_limiter = RateLimiter()
