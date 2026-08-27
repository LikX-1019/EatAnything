from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import SessionDep, UserDep, get_current_user, get_minio, get_token_payload
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.schemas.common import ApiResponse, PageData
from app.schemas.stores import RandomStoreData, RandomStoreRequest, StoreDetail, StoreSummary
from app.services.stores import get_user_store, random_user_store, user_store_page
from app.repositories.history import add_history
from app.repositories.stores import get_store
from app.api.v1.utils import response, store_id as parse_store_id


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
    items, total = await user_store_page(
        session,
        storage,
        user.id,
        keyword=keyword,
        page=page,
        page_size=page_size,
        school_id=user.school_id,
    )
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@router.post("/random", response_model=ApiResponse[RandomStoreData])
async def random_store(
    payload: RandomStoreRequest | None,
    request: Request,
    token_payload: Annotated[dict[str, Any], Depends(get_token_payload)],
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
):
    if token_payload.get("kind") != "user":
        raise ApiError(403, "FORBIDDEN", "当前 Token 不是用户身份")
    try:
        user_id = int(token_payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(401, "AUTH_REQUIRED", "登录状态无效") from exc

    exclude_id = parse_store_id(payload.exclude_store_id) if payload and payload.exclude_store_id else None
    school_id = payload.school_id if payload else None
    if school_id is None:
        user = await get_current_user(token_payload, session)
        school_id = user.school_id
    store, history_id = await random_user_store(session, storage, user_id, exclude_id, school_id)
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
    item = await add_history(session, user_id=user.id, store_id=sid, action="confirmed_pick")
    await session.commit()
    return response(request, {"id": str(item.id), "action": "CONFIRMED_PICK", "store_id": str(sid)})
