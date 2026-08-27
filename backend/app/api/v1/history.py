from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.utils import response
from app.core.dependencies import SessionDep, UserDep, get_minio
from app.integrations.minio import MinioStorage
from app.schemas.common import ApiResponse, PageData
from app.schemas.history import HistoryItem
from app.repositories.history import count_history, list_history
from app.services.history import history_view


router = APIRouter(prefix="/me/history", tags=["History"])


@router.get("", response_model=ApiResponse[PageData[HistoryItem]])
async def my_history(request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio), action: str | None = Query(default=None), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    # 历史记录只展示用户点击“就吃这家！”确认过的店铺。
    normalized = "confirmed_pick"
    if action:
        normalized = {"CONFIRMED_PICK": "confirmed_pick"}.get(action.upper())
        if normalized is None:
            from app.core.errors import ApiError

            raise ApiError(400, "INVALID_ARGUMENT", "action 必须是 CONFIRMED_PICK", field="action")
    items = await list_history(session, user.id, action=normalized, page=page, page_size=page_size)
    total = await count_history(session, user.id, action=normalized)
    return response(request, {"items": [history_view(item, storage) for item in items], "page": page, "page_size": page_size, "total": total})
