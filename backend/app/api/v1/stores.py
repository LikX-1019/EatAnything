from fastapi import APIRouter, Query, Request

from app.core.dependencies import SessionDep, UserDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.schemas.common import ApiResponse, PageData
from app.schemas.stores import RandomStoreRequest, StoreDetail, StoreSummary
from app.services.stores import get_user_store, random_user_store, user_store_page
from app.repositories.history import add_history
from app.repositories.stores import get_store
from app.api.v1.utils import response, store_id as parse_store_id
from fastapi import Depends


router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("", response_model=ApiResponse[PageData[StoreSummary]])
async def list_stores(
    request: Request,
    user: UserDep,
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
    keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = await user_store_page(session, storage, user.id, keyword=keyword, page=page, page_size=page_size)
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@router.post("/random", response_model=ApiResponse[dict])
async def random_store(payload: RandomStoreRequest | None, request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    exclude_id = parse_store_id(payload.exclude_store_id) if payload and payload.exclude_store_id else None
    store, history_id = await random_user_store(session, storage, user.id, exclude_id)
    return response(request, {"store": store, "history_id": history_id})


@router.get("/{storeId}", response_model=ApiResponse[StoreDetail])
async def store_detail(storeId: str, request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    data = await get_user_store(session, storage, user.id, parse_store_id(storeId))
    return response(request, data)


@router.post("/{storeId}/visits", response_model=ApiResponse[dict], status_code=201)
async def record_visit(storeId: str, request: Request, user: UserDep, session: SessionDep):
    sid = parse_store_id(storeId)
    store = await get_store(session, sid, active_only=True)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已不可用")
    item = await add_history(session, user_id=user.id, store_id=sid, action="store_view")
    await session.commit()
    return response(request, {"id": str(item.id), "action": "DETAIL_VIEW", "store_id": str(sid)})
