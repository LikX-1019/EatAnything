from __future__ import annotations

import time

import httpx

from app.core.config import Settings
from app.core.errors import ApiError


class WechatClient:
    endpoint = "https://api.weixin.qq.com/sns/jscode2session"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

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

    async def access_token(self, *, force: bool = False) -> str:
        if not force and self._access_token and self._access_token_expires_at > time.monotonic() + 60:
            return self._access_token
        if not self.settings.wechat_app_id or not self.settings.wechat_app_secret:
            raise WechatSendError("WECHAT_NOT_CONFIGURED", "微信服务尚未配置", transient=False)
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    "https://api.weixin.qq.com/cgi-bin/token",
                    params={"grant_type": "client_credential", "appid": self.settings.wechat_app_id, "secret": self.settings.wechat_app_secret},
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WechatSendError("WECHAT_UNAVAILABLE", "微信访问令牌服务暂时不可用", transient=True) from exc
        if not data.get("access_token"):
            raise WechatSendError(str(data.get("errcode", "TOKEN_FAILED")), str(data.get("errmsg", "获取微信访问令牌失败")), transient=True)
        self._access_token = str(data["access_token"])
        self._access_token_expires_at = time.monotonic() + int(data.get("expires_in", 7200))
        return self._access_token

    async def send_subscribe_message(self, *, openid: str, template_id: str, page: str, data: dict) -> None:
        token = await self.access_token()
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    "https://api.weixin.qq.com/cgi-bin/message/subscribe/send",
                    params={"access_token": token},
                    json={"touser": openid, "template_id": template_id, "page": page, "data": data, "miniprogram_state": "formal"},
                )
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WechatSendError("WECHAT_UNAVAILABLE", "微信订阅消息服务暂时不可用", transient=True) from exc
        code = int(result.get("errcode", 0))
        if code == 0:
            return
        if code in {40001, 40014, 42001}:
            self._access_token = None
        transient = code in {-1, 40001, 40014, 42001, 45009}
        raise WechatSendError(str(code), str(result.get("errmsg", "微信订阅消息发送失败")), transient=transient)


class WechatSendError(Exception):
    def __init__(self, code: str, message: str, *, transient: bool):
        super().__init__(message)
        self.code = code
        self.transient = transient
