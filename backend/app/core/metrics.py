"""轻量级 Prometheus 文本指标收集器。

项目不额外引入重量级指标依赖，指标只按 HTTP 方法、路径模板和状态码聚合，
避免把用户标识、Token 或请求内容写入指标标签。
"""

from __future__ import annotations

from collections import Counter
from threading import Lock


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._request_duration_ms: Counter[tuple[str, str]] = Counter()
        self._exceptions = 0

    def observe_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        # 仅记录受控路径，避免动态 ID 造成高基数指标。
        normalized_path = self._normalize_path(path)
        with self._lock:
            self._requests[(method.upper(), normalized_path, status_code)] += 1
            self._request_duration_ms[(method.upper(), normalized_path)] += int(duration_ms)

    def observe_exception(self) -> None:
        with self._lock:
            self._exceptions += 1

    def render(self) -> str:
        lines = [
            "# HELP eatanything_http_requests_total HTTP requests handled by the API.",
            "# TYPE eatanything_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), count in sorted(self._requests.items()):
                lines.append(
                    f'eatanything_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP eatanything_http_request_duration_ms_total Total request duration in milliseconds.",
                    "# TYPE eatanything_http_request_duration_ms_total counter",
                ]
            )
            for (method, path), duration in sorted(self._request_duration_ms.items()):
                lines.append(
                    f'eatanything_http_request_duration_ms_total{{method="{method}",path="{path}"}} {duration}'
                )
            lines.extend(
                [
                    "# HELP eatanything_unhandled_exceptions_total Unhandled application exceptions.",
                    "# TYPE eatanything_unhandled_exceptions_total counter",
                    f"eatanything_unhandled_exceptions_total {self._exceptions}",
                ]
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _normalize_path(path: str) -> str:
        if path.startswith("/api/v1/stores/"):
            return "/api/v1/stores/:id"
        if path.startswith("/api/v1/admin/stores/"):
            return "/api/v1/admin/stores/:id"
        if path.startswith("/api/v1/admin/uploads/"):
            return "/api/v1/admin/uploads/:action"
        return path


metrics = Metrics()
