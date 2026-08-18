from datetime import datetime

from app.schemas.common import ApiResponse, PageData, SchemaBase


class CheckInItem(SchemaBase):
    id: str
    store_id: str
    photo_url: str
    note: str | None = None
    checked_at: datetime
    created_at: datetime


CheckInResponse = ApiResponse[CheckInItem]
CheckInListResponse = ApiResponse[PageData[CheckInItem]]
