from collections.abc import Mapping
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        field: str | None = None,
        details: list[Mapping[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.details = details or []
        self.headers = headers or {}


def error_payload(request: Request, error: ApiError) -> dict[str, Any]:
    body: dict[str, Any] = {
        "status": error.status_code,
        "code": error.code,
        "message": error.message,
    }
    if error.field:
        body["field"] = error.field
    if error.details:
        body["details"] = error.details
    return {"error": body, "requestId": getattr(request.state, "request_id", "unknown")}


async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(error_payload(request, error), status_code=error.status_code, headers=error.headers)


async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    details = []
    for item in error.errors():
        location = item.get("loc", ())
        field = ".".join(str(part) for part in location if part not in {"body", "query", "path"})
        details.append({"field": field or None, "code": "INVALID_ARGUMENT", "message": item.get("msg", "参数不合法")})
    api_error = ApiError(400, "INVALID_ARGUMENT", "请求参数不合法", details=details)
    return await api_error_handler(request, api_error)


async def http_error_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
    api_error = ApiError(error.status_code, "HTTP_ERROR", str(error.detail))
    return await api_error_handler(request, api_error)


async def integrity_error_handler(request: Request, error: IntegrityError) -> JSONResponse:
    message = str(error.orig).lower()
    if "stores" in message and ("store_code" in message or "uq_stores_store_code" in message):
        code = "STORE_CODE_CONFLICT"
        text = "店铺编码已存在"
    elif "admin_users" in message or "username" in message:
        code = "ADMIN_USERNAME_CONFLICT"
        text = "管理员账号已存在"
    elif "reviews" in message:
        code = "REVIEW_CONFLICT"
        text = "该店铺已有当前用户的评价"
    else:
        code = "RESOURCE_CONFLICT"
        text = "资源已存在或发生冲突"
    return await api_error_handler(request, ApiError(409, code, text))


async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
    request.app.state.logger.exception("unhandled_error", error_type=type(error).__name__)
    return await api_error_handler(request, ApiError(500, "INTERNAL_ERROR", "服务暂时不可用"))
