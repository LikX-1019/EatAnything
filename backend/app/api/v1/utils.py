from fastapi import Request

from app.core.errors import ApiError


def store_id(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ApiError(400, "INVALID_ARGUMENT", "storeId 必须是数字", field="storeId") from exc
    if parsed <= 0:
        raise ApiError(400, "INVALID_ARGUMENT", "storeId 必须是正整数", field="storeId")
    return parsed


def school_id(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ApiError(400, "INVALID_ARGUMENT", "schoolId 必须是数字", field="schoolId") from exc
    if parsed <= 0:
        raise ApiError(400, "INVALID_ARGUMENT", "schoolId 必须是正整数", field="schoolId")
    return parsed


def response(request: Request, data):
    return {"data": data, "request_id": getattr(request.state, "request_id", "unknown")}
