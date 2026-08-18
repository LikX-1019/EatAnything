from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class SchemaBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ApiResponse(SchemaBase, Generic[T]):
    data: T
    request_id: str


class PageData(SchemaBase, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class ErrorDetail(SchemaBase):
    row: int | None = None
    field: str | None = None
    code: str
    message: str


class ErrorBody(SchemaBase):
    status: int
    code: str
    message: str
    field: str | None = None
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(SchemaBase):
    error: ErrorBody
    request_id: str
