from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.users import ProfileUpdate
from app.services import users as user_service


def test_profile_update_strips_nickname() -> None:
    update = ProfileUpdate(nickname="  小明  ")
    assert update.nickname == "小明"


def test_profile_update_rejects_blank_nickname() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(nickname="   ")


def test_profile_update_rejects_future_birthday() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(birthday=date(2100, 1, 1))


def test_profile_update_rejects_too_old_birthday() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(birthday=date(1800, 1, 1))


def test_profile_update_rejects_invalid_gender() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(gender="unknown")  # type: ignore[arg-type]


def test_profile_update_accepts_valid_values() -> None:
    update = ProfileUpdate(
        nickname="同学A",
        slogan="今天也要好好吃饭",
        gender="female",
        birthday=date(2005, 6, 1),
    )
    assert update.gender == "female"
    assert update.birthday.isoformat() == "2005-06-01"


class UserSession:
    async def get(self, _model, _key):
        return SimpleNamespace(object_key="uploads/avatars/abc.jpg")


class UserStorage:
    def public_object_url(self, object_key: str) -> str:
        return f"https://cdn.test/{object_key}"


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=9,
        avatar_media_id=3,
        nickname="同学A",
        school_id=None,
        school=None,
        slogan="干饭",
        gender="male",
        birthday=date(2003, 3, 3),
        level=2,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_profile_service_returns_avatar_and_new_fields(monkeypatch) -> None:
    async def fake_stats(_session, _user_id):
        return {
            "favorite_count": 1,
            "eaten_count": 2,
            "checkin_count": 3,
            "review_count": 4,
            "history_count": 5,
        }

    monkeypatch.setattr(user_service, "user_stats", fake_stats)
    data = await user_service.profile(UserSession(), UserStorage(), _user())
    assert data["avatar_url"] == "https://cdn.test/uploads/avatars/abc.jpg"
    assert data["gender"] == "male"
    assert data["birthday"] == "2003-03-03"
    assert data["stats"]["favorite_count"] == 1
