from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.models import Review
from app.services import reviews as review_service


def store() -> SimpleNamespace:
    return SimpleNamespace(
        id=2,
        status="active",
        store_code="noodle-house",
        name="面馆",
        address="东门",
        area=SimpleNamespace(name="东区"),
        categories=[],
        images=[],
    )


class ReviewSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    def add(self, value):
        self.added.append(value)
        if isinstance(value, Review):
            value.id = 10
            value.created_at = datetime.now(timezone.utc)
            value.updated_at = value.created_at
            value.store = store()
            value.user = SimpleNamespace(nickname="测试同学", avatar=None)

    async def commit(self):
        return None

    async def refresh(self, _value):
        return None


class Storage:
    def public_object_url(self, _key):
        return "https://cdn.test/avatar.jpg"


@pytest.mark.asyncio
async def test_review_requires_check_in(monkeypatch) -> None:
    monkeypatch.setattr(review_service, "get_store", lambda *_args, **_kwargs: _store())
    monkeypatch.setattr(review_service, "get_user_review", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(review_service, "latest_check_in", lambda *_args, **_kwargs: _none())

    with pytest.raises(ApiError) as error:
        await review_service.upsert_review(ReviewSession(), Storage(), 1, 2, 5, "很好吃")

    assert error.value.code == "REVIEW_REQUIRES_CHECK_IN"


@pytest.mark.asyncio
async def test_review_create_uses_latest_check_in(monkeypatch) -> None:
    check_in = SimpleNamespace(id=7)
    monkeypatch.setattr(review_service, "get_store", lambda *_args, **_kwargs: _store())
    monkeypatch.setattr(review_service, "get_user_review", lambda *_args, **_kwargs: _none())
    monkeypatch.setattr(review_service, "latest_check_in", lambda *_args, **_kwargs: _value(check_in))

    session = ReviewSession()
    result = await review_service.upsert_review(session, Storage(), 1, 2, 4, "  份量足  ")

    created = session.added[0]
    assert result["rating"] == 4
    assert result["content"] == "份量足"
    assert created.check_in_id == 7


@pytest.mark.asyncio
async def test_review_update_keeps_one_review(monkeypatch) -> None:
    existing = Review(id=10, user_id=1, store_id=2, check_in_id=7, rating=3, content="旧评价", status="published")
    existing.store = store()
    existing.user = SimpleNamespace(nickname="测试同学", avatar=None)
    existing.created_at = datetime.now(timezone.utc)
    existing.updated_at = existing.created_at
    monkeypatch.setattr(review_service, "get_store", lambda *_args, **_kwargs: _store())
    monkeypatch.setattr(review_service, "get_user_review", lambda *_args, **_kwargs: _value(existing))
    monkeypatch.setattr(review_service, "latest_check_in", lambda *_args, **_kwargs: _value(SimpleNamespace(id=7)))

    session = ReviewSession(existing)
    result = await review_service.upsert_review(session, Storage(), 1, 2, 5, "  更新后的评价 ")

    assert result["id"] == "10"
    assert result["rating"] == 5
    assert result["content"] == "更新后的评价"
    assert session.added == []


async def _store():
    return store()


async def _none():
    return None


async def _value(value):
    return value
