from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.api.v1 import stores as stores_api
from app.core.errors import ApiError
from app.schemas.stores import RandomStoreRequest


def request() -> Request:
    value = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/stores/random",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("test", 80),
            "scheme": "http",
        }
    )
    value.state.request_id = "req_test"
    return value


async def test_random_store_uses_request_school_without_extra_user_query(monkeypatch) -> None:
    captured = {}

    async def draw(_session, _storage, user_id, exclude_store_id, school_id):
        captured.update(
            user_id=user_id,
            exclude_store_id=exclude_store_id,
            school_id=school_id,
        )
        return {"id": "2"}, ""

    async def unexpected_user_query(*_args):
        raise AssertionError("快速抽取路径不应额外查询用户")

    monkeypatch.setattr(stores_api, "random_user_store", draw)
    monkeypatch.setattr(stores_api, "get_current_user", unexpected_user_query)

    result = await stores_api.random_store(
        RandomStoreRequest(schoolId=9, excludeStoreId="1"),
        request(),
        {"kind": "user", "sub": "7"},
        object(),
        object(),
    )

    assert captured == {"user_id": 7, "exclude_store_id": 1, "school_id": 9}
    assert result == {"data": {"store": {"id": "2"}, "history_id": ""}, "request_id": "req_test"}


async def test_random_store_keeps_compatibility_for_payload_without_school(monkeypatch) -> None:
    captured = {}

    async def load_user(_payload, _session):
        return SimpleNamespace(school_id=8)

    async def draw(_session, _storage, user_id, exclude_store_id, school_id):
        captured.update(user_id=user_id, school_id=school_id)
        return {"id": "3"}, ""

    monkeypatch.setattr(stores_api, "get_current_user", load_user)
    monkeypatch.setattr(stores_api, "random_user_store", draw)

    await stores_api.random_store(
        RandomStoreRequest(),
        request(),
        {"kind": "user", "sub": "7"},
        object(),
        object(),
    )

    assert captured == {"user_id": 7, "school_id": 8}


async def test_random_store_rejects_admin_token() -> None:
    with pytest.raises(ApiError) as error:
        await stores_api.random_store(
            RandomStoreRequest(schoolId=9),
            request(),
            {"kind": "admin", "sub": "1"},
            object(),
            object(),
        )

    assert error.value.code == "FORBIDDEN"
