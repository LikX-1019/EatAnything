from datetime import date
from typing import Literal

from pydantic import field_validator

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
    gender: str | None = None
    birthday: str | None = None
    level: int
    stats: UserStats
    created_at: str


UserProfileResponse = ApiResponse[UserProfile]


class ProfileUpdate(SchemaBase):
    nickname: str | None = None
    slogan: str | None = None
    gender: Literal["male", "female", "other", "secret"] | None = None
    birthday: date | None = None

    @field_validator("nickname")
    @classmethod
    def nickname_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("昵称不能为空")
        return stripped

    @field_validator("birthday")
    @classmethod
    def birthday_in_range(cls, value: date | None) -> date | None:
        if value is None:
            return value
        if value < date(1900, 1, 1) or value > date.today():
            raise ValueError("生日必须介于 1900-01-01 与今天之间")
        return value


class AvatarUploadData(SchemaBase):
    avatar_url: str
