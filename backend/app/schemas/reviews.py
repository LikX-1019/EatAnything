from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import ApiResponse, PageData, SchemaBase
from app.schemas.history import StoreSnapshot


class Reviewer(SchemaBase):
    display_name: str
    avatar_url: str | None = None


class ReviewItem(SchemaBase):
    id: str
    store_id: str
    check_in_id: str | None = None
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=500)
    reviewer: Reviewer
    created_at: datetime
    updated_at: datetime


class MyReview(SchemaBase):
    id: str
    store: StoreSnapshot
    check_in_id: str | None = None
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=500)
    created_at: datetime
    updated_at: datetime


class ReviewUpsertRequest(SchemaBase):
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value: str) -> str:
        return str(value).strip()


ReviewListResponse = ApiResponse[PageData[ReviewItem]]
MyReviewListResponse = ApiResponse[PageData[MyReview]]
MyReviewResponse = ApiResponse[MyReview]
