from fastapi import APIRouter, Request

from app.core.dependencies import SessionDep, SettingsDep
from app.core.errors import ApiError
from app.integrations.wechat import WechatClient
from app.schemas.auth import AuthData, DevLoginRequest, WechatLoginRequest
from app.schemas.common import ApiResponse
from app.services.auth import login_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/wechat-login", response_model=ApiResponse[AuthData])
async def wechat_login(payload: WechatLoginRequest, request: Request, session: SessionDep, settings: SettingsDep):
    external_id = await WechatClient(settings).exchange_code(payload.code)
    data = await login_user(session, settings, external_id=f"wechat:{external_id}")
    return {"data": data, "request_id": request.state.request_id}


@router.post("/dev-login", response_model=ApiResponse[AuthData])
async def dev_login(payload: DevLoginRequest, request: Request, session: SessionDep, settings: SettingsDep):
    if not settings.dev_auth_enabled or settings.app_env.lower() in {"production", "prod"}:
        raise ApiError(404, "NOT_FOUND", "开发登录未启用")
    data = await login_user(session, settings, external_id=payload.external_id, nickname="干饭小能手")
    return {"data": data, "request_id": request.state.request_id}
