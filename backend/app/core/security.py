from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import Settings
from app.core.errors import ApiError


password_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(settings: Settings, *, subject: str, kind: str, role: str | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "kind": kind,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_expire_seconds),
    }
    if role:
        payload["role"] = role
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ApiError(401, "AUTH_REQUIRED", "登录状态已失效") from exc
    if not payload.get("sub") or payload.get("kind") not in {"user", "admin"}:
        raise ApiError(401, "AUTH_REQUIRED", "登录状态无效")
    return payload
