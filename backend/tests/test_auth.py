import logging
from types import SimpleNamespace

from app.core.logging import configure_logging
from app.services.auth import user_auth_response


class UserWithLazyAvatar:
    id = 7
    nickname = "测试用户"
    avatar_media_id = 3

    @property
    def avatar(self):
        raise AssertionError("登录响应不应触发头像关系懒加载")


def test_user_auth_response_does_not_load_avatar_relationship() -> None:
    settings = SimpleNamespace(jwt_secret="a" * 48, jwt_expire_seconds=3600)

    result = user_auth_response(settings, UserWithLazyAvatar())  # type: ignore[arg-type]

    assert result["user"] == {
        "id": "7",
        "nickname": "测试用户",
        "avatar_url": "/api/v1/me/avatar/file",
    }
    assert result["access_token"]


def test_httpx_request_logging_does_not_emit_sensitive_urls() -> None:
    configure_logging()

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
