from io import BytesIO
from inspect import signature
from types import SimpleNamespace

import pytest
from PIL import Image

from app.core.errors import ApiError
from app.repositories.states import set_favorite
from app.services import checkins as checkins_service
from app.services.checkins import create_check_in, validate_check_in_image
from app.services.stores import user_store_page


def image_bytes(image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format=image_format)
    return buffer.getvalue()


class FavoriteSession:
    def __init__(self) -> None:
        self.favorite = None
        self.added = []
        self.deleted = []

    async def get(self, _model, _key):
        return self.favorite

    def add(self, value):
        self.added.append(value)
        self.favorite = value

    async def flush(self):
        return None

    async def delete(self, value):
        self.deleted.append(value)
        self.favorite = None


@pytest.mark.asyncio
async def test_duplicate_favorite_add_is_idempotent() -> None:
    session = FavoriteSession()

    first = await set_favorite(session, user_id=1, store_id=2, enabled=True)
    second = await set_favorite(session, user_id=1, store_id=2, enabled=True)

    assert first is second
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_favorite_can_be_added_and_removed() -> None:
    session = FavoriteSession()

    added = await set_favorite(session, user_id=1, store_id=2, enabled=True)
    removed = await set_favorite(session, user_id=1, store_id=2, enabled=False)

    assert added is not None
    assert removed is None
    assert session.favorite is None
    assert session.deleted == [added]


class CheckInSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if value.__class__.__name__ == "MediaObject":
                value.id = 3

    async def commit(self):
        return None

    async def refresh(self, _value):
        return None

    async def get(self, _model, _key):
        return None


class CheckInStorage:
    bucket = "media"

    def __init__(self) -> None:
        self.uploads = []

    async def put_bytes(self, object_key, content, content_type):
        self.uploads.append((object_key, content, content_type))

    async def remove(self, _object_key):
        return None

    def public_object_url(self, object_key):
        return f"https://cdn.test/{object_key}"


@pytest.mark.asyncio
async def test_check_in_creation_persists_the_eaten_state(monkeypatch) -> None:
    monkeypatch.setattr(checkins_service, "get_store", lambda *_args, **_kwargs: _existing_store())
    session = CheckInSession()
    storage = CheckInStorage()

    result = await create_check_in(
        session,
        storage,
        user_id=1,
        store_id=2,
        content=image_bytes(),
        original_filename="meal.png",
        note="午餐",
    )

    assert result["store_id"] == "2"
    assert result["photo_url"].startswith("https://cdn.test/uploads/users/1/checkins/")
    assert any(value.__class__.__name__ == "CheckIn" and value.store_id == 2 for value in session.added)


async def _existing_store():
    return SimpleNamespace(school_id=1)


def test_check_in_requires_a_valid_image() -> None:
    with pytest.raises(ApiError) as missing:
        validate_check_in_image(b"")
    assert missing.value.code == "IMAGE_REQUIRED"

    with pytest.raises(ApiError) as invalid:
        validate_check_in_image(b"not-an-image")
    assert invalid.value.code == "UNSUPPORTED_FILE_TYPE"

    content_type, extension, width, height = validate_check_in_image(image_bytes("JPEG"))
    assert (content_type, extension, width, height) == ("image/jpeg", "jpg", 4, 4)


@pytest.mark.asyncio
async def test_store_state_without_school_has_no_current_school_items() -> None:
    session = SimpleNamespace()
    items, total = await user_store_page(
        session,
        storage=SimpleNamespace(),
        user_id=1,
        keyword=None,
        page=1,
        page_size=20,
        mode="favorites",
        school_id=None,
    )
    assert items == []
    assert total == 0


def test_history_query_keeps_user_history_across_school_switch() -> None:
    from app.repositories.history import list_history

    # 仓储层接口只按用户和行为筛选；切换当前学校不能删除历史记录。
    assert "school_id" not in signature(list_history).parameters
