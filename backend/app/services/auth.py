from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.security import create_access_token, verify_password
from app.models import AppUser
from app.repositories.admins import get_admin_by_username
from app.repositories.users import get_or_create_user


def user_auth_response(settings: Settings, user: AppUser) -> dict:
    # 登录响应只使用已加载的外键字段，避免异步会话隐式触发头像关系查询。
    avatar_url = "/api/v1/me/avatar/file" if user.avatar_media_id else None
    return {
        "access_token": create_access_token(settings, subject=str(user.id), kind="user"),
        "token_type": "Bearer",
        "expires_in": settings.jwt_expire_seconds,
        "user": {"id": str(user.id), "nickname": user.nickname, "avatar_url": avatar_url},
    }


async def login_user(
    session: AsyncSession,
    settings: Settings,
    *,
    external_id: str,
    nickname: str = "微信用户",
) -> dict:
    user = await get_or_create_user(session, external_id=external_id, nickname=nickname)
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    return user_auth_response(settings, user)


async def login_admin(session: AsyncSession, settings: Settings, username: str, password: str) -> dict:
    admin = await get_admin_by_username(session, username.strip())
    if admin is None or admin.status != "active" or not verify_password(password, admin.password_hash):
        raise ApiError(401, "LOGIN_FAILED", "账号或密码错误")
    admin.last_login_at = datetime.now(UTC)
    await session.commit()
    token = create_access_token(settings, subject=str(admin.id), kind="admin", role=admin.role)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.jwt_expire_seconds,
        "admin": {"id": str(admin.id), "username": admin.username, "display_name": admin.display_name, "roles": [admin.role]},
    }
