from app.main import app


def test_required_paths_are_exposed() -> None:
    paths = app.openapi()["paths"]
    required = {
        "/health/live",
        "/health/ready",
        "/api/v1/auth/wechat-login",
        "/api/v1/auth/dev-login",
        "/api/v1/admin/auth/login",
        "/api/v1/me",
        "/api/v1/stores",
        "/api/v1/stores/random",
        "/api/v1/stores/{storeId}",
        "/api/v1/stores/{storeId}/visits",
        "/api/v1/stores/{storeId}/reviews",
        "/api/v1/me/favorites",
        "/api/v1/me/favorites/{storeId}",
        "/api/v1/me/eaten",
        "/api/v1/me/eaten/{storeId}",
        "/api/v1/stores/{storeId}/check-ins",
        "/api/v1/me/check-ins",
        "/api/v1/me/history",
        "/api/v1/me/reviews",
        "/api/v1/me/reviews/{storeId}",
        "/api/v1/admin/stores",
        "/api/v1/admin/stores/import",
        "/api/v1/admin/stores/{storeId}",
        "/api/v1/admin/uploads/images",
        "/api/v1/me/messages",
        "/api/v1/me/messages/unread-count",
        "/api/v1/me/messages/{messageId}",
        "/api/v1/me/announcements/home",
        "/api/v1/me/notification-settings",
        "/api/v1/me/avatar",
        "/api/v1/me/avatar/data",
        "/api/v1/me/avatar/file",
        "/api/v1/admin/messages",
        "/api/v1/admin/messages/{messageId}",
        "/api/v1/admin/messages/images",
    }
    assert required <= set(paths)


def test_admin_status_schema_uses_database_values() -> None:
    schema = app.openapi()["components"]["schemas"]["AdminStoreCreateRequest"]
    assert schema["properties"]["status"]["pattern"] == "^(active|hidden|closed)$"


def test_random_store_response_uses_camel_case_fields() -> None:
    schema = app.openapi()["components"]["schemas"]["RandomStoreData"]
    assert "historyId" in schema["properties"]
    assert "history_id" not in schema["properties"]
