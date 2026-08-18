from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.errors import ApiError


class WechatClient:
    endpoint = "https://api.weixin.qq.com/sns/jscode2session"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def exchange_code(self, code: str) -> str:
        if not self.settings.wechat_app_id or not self.settings.wechat_app_secret:
            raise ApiError(503, "WECHAT_NOT_CONFIGURED", "微信登录尚未配置")
        params = {
            "appid": self.settings.wechat_app_id,
            "secret": self.settings.wechat_app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ApiError(503, "WECHAT_UNAVAILABLE", "微信登录服务暂时不可用") from exc
        if data.get("errcode") or not data.get("openid"):
            raise ApiError(401, "WECHAT_CODE_INVALID", "微信登录凭据无效")
        return str(data["openid"])
