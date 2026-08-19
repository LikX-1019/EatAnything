from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.utils import response, store_id as parse_store_id
from app.core.dependencies import SessionDep, UserDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.repositories.states import set_favorite
from app.repositories.stores import get_store
from app.schemas.common import ApiResponse, PageData
from app.schemas.stores import EatenState, FavoriteState, StoreSummary
from app.services.stores import user_store_page


favorite_router = APIRouter(prefix="/me/favorites", tags=["Favorites"])
eaten_router = APIRouter(prefix="/me/eaten", tags=["Eaten"])


@favorite_router.get("", response_model=ApiResponse[PageData[StoreSummary]])
async def list_favorites(request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio), keyword: str | None = Query(default=None, max_length=100), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    items, total = await user_store_page(
        session,
        storage,
        user.id,
        keyword=keyword,
        page=page,
        page_size=page_size,
        mode="favorites",
        school_id=user.school_id,
    )
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@favorite_router.put("/{storeId}", response_model=ApiResponse[FavoriteState])
async def add_favorite(storeId: str, request: Request, user: UserDep, session: SessionDep):
    sid = parse_store_id(storeId)
    if await get_store(session, sid, active_only=True) is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已不可用")
    await set_favorite(session, user.id, sid, True)
    await session.commit()
    return response(request, {"store_id": str(sid), "is_favorite": True})


@favorite_router.delete("/{storeId}", response_model=ApiResponse[FavoriteState])
async def remove_favorite(storeId: str, request: Request, user: UserDep, session: SessionDep):
    sid = parse_store_id(storeId)
    if await get_store(session, sid, active_only=False) is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在")
    await set_favorite(session, user.id, sid, False)
    await session.commit()
    return response(request, {"store_id": str(sid), "is_favorite": False})


@eaten_router.get("", response_model=ApiResponse[PageData[StoreSummary]])
async def list_eaten(request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio), keyword: str | None = Query(default=None, max_length=100), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    items, total = await user_store_page(
        session,
        storage,
        user.id,
        keyword=keyword,
        page=page,
        page_size=page_size,
        mode="eaten",
        school_id=user.school_id,
    )
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@eaten_router.put("/{storeId}", response_model=ApiResponse[EatenState])
async def mark_eaten(storeId: str, request: Request, user: UserDep, session: SessionDep):
    raise ApiError(400, "CHECK_IN_IMAGE_REQUIRED", "打卡必须上传图片，请使用店铺打卡接口")


@eaten_router.delete("/{storeId}", response_model=ApiResponse[EatenState])
async def unmark_eaten(storeId: str, request: Request, user: UserDep, session: SessionDep):
    raise ApiError(409, "CHECK_IN_IMMUTABLE", "打卡是到店记录，不能通过取消吃过状态删除")
