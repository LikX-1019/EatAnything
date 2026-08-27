from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.integrations.minio import MinioStorage
from app.integrations.wechat import WechatClient
from app.models import AdminUser, AppUser
from app.repositories.users import get_user_by_id


bearer_scheme = HTTPBearer(auto_error=False)
SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_minio(settings: SettingsDep) -> MinioStorage:
    return MinioStorage(settings)


def get_wechat(settings: SettingsDep) -> WechatClient:
    return WechatClient(settings)


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: SettingsDep,
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "AUTH_REQUIRED", "需要登录")
    return decode_access_token(settings, credentials.credentials)


async def get_current_user(payload: Annotated[dict[str, Any], Depends(get_token_payload)], session: SessionDep) -> AppUser:
    if payload.get("kind") != "user":
        raise ApiError(403, "FORBIDDEN", "当前 Token 不是用户身份")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(401, "AUTH_REQUIRED", "登录状态无效") from exc
    user = await get_user_by_id(session, user_id)
    if user is None or user.status != "active":
        raise ApiError(401, "AUTH_REQUIRED", "用户不存在或已失效")
    return user


async def get_current_admin(payload: Annotated[dict[str, Any], Depends(get_token_payload)], session: SessionDep) -> AdminUser:
    if payload.get("kind") != "admin" or payload.get("role") not in {"store_admin", "platform_admin", "school_admin"}:
        raise ApiError(403, "FORBIDDEN", "需要管理员权限")
    try:
        admin_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(401, "AUTH_REQUIRED", "登录状态无效") from exc
    admin = await session.get(AdminUser, admin_id)
    if admin is None or admin.status != "active":
        raise ApiError(401, "AUTH_REQUIRED", "管理员账号不存在或已禁用")
    return admin


UserDep = Annotated[AppUser, Depends(get_current_user)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
