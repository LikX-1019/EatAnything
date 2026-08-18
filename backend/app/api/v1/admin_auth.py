from fastapi import APIRouter, Request

from app.core.dependencies import SessionDep, SettingsDep
from app.schemas.auth import AdminAuthData, AdminLoginRequest
from app.schemas.common import ApiResponse
from app.services.auth import login_admin


router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])


@router.post("/login", response_model=ApiResponse[AdminAuthData])
async def login(payload: AdminLoginRequest, request: Request, session: SessionDep, settings: SettingsDep):
    data = await login_admin(session, settings, payload.username, payload.password)
    return {"data": data, "request_id": request.state.request_id}
