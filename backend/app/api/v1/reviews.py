from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.utils import response, store_id as parse_store_id
from app.core.dependencies import SessionDep, UserDep, get_minio
from app.integrations.minio import MinioStorage
from app.repositories.reviews import get_user_review
from app.schemas.common import ApiResponse, PageData
from app.schemas.reviews import MyReview, ReviewItem, ReviewUpsertRequest
from app.services.reviews import store_reviews_page, upsert_review, user_reviews_page


router = APIRouter(tags=["Reviews"])


@router.get("/stores/{storeId}/reviews", response_model=ApiResponse[PageData[ReviewItem]])
async def store_reviews(storeId: str, request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    items, total = await store_reviews_page(session, storage, parse_store_id(storeId), page, page_size)
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/me/reviews", response_model=ApiResponse[PageData[MyReview]])
async def my_reviews(request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    items, total = await user_reviews_page(session, storage, user.id, page, page_size)
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@router.put("/me/reviews/{storeId}", response_model=ApiResponse[MyReview])
async def save_review(storeId: str, payload: ReviewUpsertRequest, request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    data = await upsert_review(session, storage, user.id, parse_store_id(storeId), payload.rating, payload.content)
    return response(request, data)


@router.delete("/me/reviews/{storeId}", status_code=204)
async def delete_review(storeId: str, user: UserDep, session: SessionDep):
    review = await get_user_review(session, user.id, parse_store_id(storeId))
    if review:
        await session.delete(review)
        await session.commit()
    return None
