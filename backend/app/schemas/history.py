from datetime import datetime

from app.schemas.common import ApiResponse, PageData, SchemaBase


class StoreSnapshot(SchemaBase):
    id: str
    store_code: str
    name: str
    category: str
    address: str
    area: str = ""
    image_url: str | None = None
    is_available: bool


class HistoryItem(SchemaBase):
    id: str
    action: str
    occurred_at: datetime
    store: StoreSnapshot


HistoryListResponse = ApiResponse[PageData[HistoryItem]]
