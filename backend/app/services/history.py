from app.integrations.minio import MinioStorage
from app.services.stores import categories_text, primary_image_url


def history_view(item, storage: MinioStorage) -> dict:
    store = item.store
    return {
        "id": str(item.id),
        "action": "RANDOM_PICK" if item.action == "random_pick" else "DETAIL_VIEW",
        "occurred_at": item.occurred_at,
        "store": {
            "id": str(store.id),
            "store_code": store.slug,
            "name": store.name,
            "category": categories_text(store),
            "address": store.address,
            "area": store.area,
            "image_url": primary_image_url(store, storage),
            "is_available": store.status == "active",
        },
    }
