from typing import Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import SchemaBase


class StoreSummary(SchemaBase):
    id: str
    store_code: str
    school_id: str | None = None
    school_code: str | None = None
    school_name: str | None = None
    name: str
    category: str
    address: str
    area: str = ""
    image_url: str | None = None
    score: float | None = None
    review_count: int = 0
    is_favorite: bool = False
    is_eaten: bool = False


class StoreDetail(StoreSummary):
    description: str | None = None
    city: str | None = None
    district: str | None = None
    created_at: str
    updated_at: str


class RandomStoreRequest(SchemaBase):
    exclude_store_id: str | None = None


class FavoriteState(SchemaBase):
    store_id: str
    is_favorite: bool


class EatenState(SchemaBase):
    store_id: str
    is_eaten: bool


class StoreImportItem(SchemaBase):
    row: int
    store_code: str
    store_id: str
    action: str


class StoreImportData(SchemaBase):
    total_rows: int
    created_count: int
    updated_count: int
    items: list[StoreImportItem]


class AdminStore(SchemaBase):
    id: str
    store_code: str
    school_id: str | None = None
    school_code: str | None = None
    school_name: str | None = None
    name: str
    category: str
    address: str
    area: str = ""
    image_url: str | None = None
    status: str
    score: float | None = None
    review_count: int = 0
    version: int
    created_at: str
    updated_at: str


class AdminStoreCreateRequest(SchemaBase):
    store_code: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    school_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    address: str = Field(min_length=1, max_length=200)
    area: str = Field(default="", max_length=100)
    image_url: str | None = None
    status: str = Field(default="hidden", pattern="^(active|hidden|closed)$")

    @field_validator("store_code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("name", "category", "address", "area", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return str(value).strip()


class AdminStoreUpdateRequest(SchemaBase):
    version: int = Field(ge=1)
    school_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, min_length=1, max_length=200)
    area: str | None = Field(default=None, min_length=1, max_length=100)
    image_url: str | None = None
    status: str | None = Field(default=None, pattern="^(active|hidden|closed)$")

    @field_validator("name", "category", "address", "area", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return str(value).strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.model_fields_set <= {"version"}:
            raise ValueError("至少提供一个需要修改的字段")
        return self


class ImageUploadData(SchemaBase):
    url: str
    content_type: str
    size: int
