from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.repositories.states import UserStoreFlags
from app.services import stores as store_service


async def test_random_store_pool_is_cached_and_user_state_stays_fresh(monkeypatch) -> None:
    store_service.clear_random_store_cache()
    calls = {"pool": 0, "stats": 0, "state": 0}
    stores = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    async def list_pool(_session, school_id):
        assert school_id == 9
        calls["pool"] += 1
        return stores

    async def load_stats(_session, store_ids):
        assert store_ids == [1, 2]
        calls["stats"] += 1
        return {}

    async def load_state(_session, user_id, school_id, store_id):
        assert school_id == 9
        calls["state"] += 1
        return UserStoreFlags(is_favorite=user_id == 11, is_eaten=store_id == 2)

    def detail(store, _storage, _stats, state=None):
        assert state is None
        return {"id": str(store.id), "is_favorite": False, "is_eaten": False}

    monkeypatch.setattr(store_service.store_repo, "list_active_stores_for_school", list_pool)
    monkeypatch.setattr(store_service.store_repo, "stats_for_stores", load_stats)
    monkeypatch.setattr(store_service, "authorized_state_for_store", load_state)
    monkeypatch.setattr(store_service, "store_detail", detail)
    monkeypatch.setattr(store_service.secrets, "choice", lambda items: items[0])

    first, _ = await store_service.random_user_store(object(), object(), 11, 1, 9)
    second, _ = await store_service.random_user_store(object(), object(), 12, 2, 9)

    assert first == {"id": "2", "is_favorite": True, "is_eaten": True}
    assert second == {"id": "1", "is_favorite": False, "is_eaten": False}
    assert calls == {"pool": 1, "stats": 1, "state": 2}
    store_service.clear_random_store_cache()


async def test_random_store_pool_is_separated_by_school(monkeypatch) -> None:
    store_service.clear_random_store_cache()
    loaded_schools = []

    async def list_pool(_session, school_id):
        loaded_schools.append(school_id)
        return [SimpleNamespace(id=school_id)]

    async def load_stats(_session, _store_ids):
        return {}

    async def load_state(_session, _user_id, _school_id, _store_id):
        return UserStoreFlags()

    monkeypatch.setattr(store_service.store_repo, "list_active_stores_for_school", list_pool)
    monkeypatch.setattr(store_service.store_repo, "stats_for_stores", load_stats)
    monkeypatch.setattr(store_service, "authorized_state_for_store", load_state)
    monkeypatch.setattr(
        store_service,
        "store_detail",
        lambda store, _storage, _stats, state=None: {
            "id": str(store.id),
            "is_favorite": False,
            "is_eaten": False,
        },
    )

    first, _ = await store_service.random_user_store(object(), object(), 1, None, 3)
    second, _ = await store_service.random_user_store(object(), object(), 1, None, 4)

    assert first["id"] == "3"
    assert second["id"] == "4"
    assert loaded_schools == [3, 4]
    store_service.clear_random_store_cache()


async def test_random_store_rejects_user_when_school_no_longer_matches(monkeypatch) -> None:
    store_service.clear_random_store_cache()

    async def list_pool(_session, _school_id):
        return [SimpleNamespace(id=5)]

    async def load_stats(_session, _store_ids):
        return {}

    async def reject_user(_session, _user_id, _school_id, _store_id):
        return None

    monkeypatch.setattr(store_service.store_repo, "list_active_stores_for_school", list_pool)
    monkeypatch.setattr(store_service.store_repo, "stats_for_stores", load_stats)
    monkeypatch.setattr(store_service, "authorized_state_for_store", reject_user)
    monkeypatch.setattr(
        store_service,
        "store_detail",
        lambda store, _storage, _stats, state=None: {
            "id": str(store.id),
            "is_favorite": False,
            "is_eaten": False,
        },
    )

    with pytest.raises(ApiError) as error:
        await store_service.random_user_store(object(), object(), 7, None, 9)

    assert error.value.code == "AUTH_REQUIRED"
    store_service.clear_random_store_cache()


def test_expired_random_store_cache_keys_are_pruned() -> None:
    store_service.clear_random_store_cache()
    store_service._random_store_pools[3] = store_service._RandomStorePool(5.0, ())
    store_service._random_store_pool_locks[3] = store_service.asyncio.Lock()
    store_service._random_store_pool_versions[3] = 1

    store_service._prune_random_store_cache(6.0)

    assert 3 not in store_service._random_store_pools
    assert 3 not in store_service._random_store_pool_locks
    assert 3 not in store_service._random_store_pool_versions


async def test_clear_random_store_cache_invalidates_inflight_population() -> None:
    store_service.clear_random_store_cache()
    lock = store_service.asyncio.Lock()
    store_service._random_store_pool_locks[9] = lock
    original_version = store_service._random_store_pool_versions.get(9, 0)

    async with lock:
        store_service.clear_random_store_cache(9)
        assert store_service._random_store_pool_versions[9] == original_version + 1

    store_service.clear_random_store_cache(9)
