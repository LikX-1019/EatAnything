from app.schemas.auth import UserSummary
from app.schemas.common import ApiResponse, SchemaBase


class SchoolSummary(SchemaBase):
    id: str
    school_code: str
    name: str
    city: str | None = None
    district: str | None = None
    address: str | None = None


class UserStats(SchemaBase):
    favorite_count: int = 0
    eaten_count: int = 0
    checkin_count: int = 0
    review_count: int = 0
    history_count: int = 0


class UserProfile(UserSummary):
    school_id: str | None = None
    school: SchoolSummary | None = None
    slogan: str | None = None
    level: int
    stats: UserStats
    created_at: str


UserProfileResponse = ApiResponse[UserProfile]
