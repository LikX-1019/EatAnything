import pytest

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "production",
        "JWT_SECRET": "a" * 48,
        "WECHAT_APP_ID": "wx-app-id",
        "WECHAT_APP_SECRET": "wx-app-secret",
        "POSTGRES_HOST": "postgres",
        "POSTGRES_PORT": 5432,
        "POSTGRES_DB": "eat_anything",
        "POSTGRES_USER": "eat_anything",
        "POSTGRES_PASSWORD": "postgres-secret-123456",
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "minio-access-1234",
        "MINIO_SECRET_KEY": "minio-secret-123456",
        "MINIO_BUCKET": "eat-anything",
        "MINIO_PRIVATE_BUCKET": "eat-anything-private",
        "MINIO_PUBLIC_URL": "https://media.unilinkcore.cn",
        "CORS_ORIGINS": "",
        "METRICS_ENABLED": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("StrongPass123!")
    assert verify_password("StrongPass123!", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_round_trip() -> None:
    settings = get_settings()
    token = create_access_token(settings, subject="42", kind="user")
    payload = decode_access_token(settings, token)
    assert payload["sub"] == "42"
    assert payload["kind"] == "user"


def test_invalid_jwt_is_rejected() -> None:
    with pytest.raises(ApiError) as error:
        decode_access_token(get_settings(), "not-a-token")
    assert error.value.status_code == 401
    assert error.value.code == "AUTH_REQUIRED"


def test_production_configuration_accepts_strong_values() -> None:
    settings = production_settings()
    assert settings.app_env == "production"


def test_production_configuration_rejects_template_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        production_settings(JWT_SECRET="change-me-generate-32-bytes-random")


def test_production_configuration_rejects_local_media_url() -> None:
    with pytest.raises(ValueError, match="MINIO_PUBLIC_URL"):
        production_settings(MINIO_PUBLIC_URL="http://127.0.0.1:9000")


def test_production_configuration_requires_metrics_token() -> None:
    with pytest.raises(ValueError, match="METRICS_TOKEN"):
        production_settings(METRICS_ENABLED=True, METRICS_TOKEN=None)


def test_wechat_subscription_configuration_fails_closed() -> None:
    with pytest.raises(ValueError, match="WECHAT_NOTIFICATION_TEMPLATE_ID"):
        production_settings(WECHAT_SUBSCRIBE_ENABLED=True)


def test_wechat_subscription_configuration_accepts_two_templates() -> None:
    settings = production_settings(
        WECHAT_SUBSCRIBE_ENABLED=True,
        WECHAT_NOTIFICATION_TEMPLATE_ID="notice-template",
        WECHAT_NOTIFICATION_TITLE_KEY="thing1",
        WECHAT_NOTIFICATION_CONTENT_KEY="thing2",
        WECHAT_NOTIFICATION_TIME_KEY="time3",
        WECHAT_ANNOUNCEMENT_TEMPLATE_ID="announcement-template",
        WECHAT_ANNOUNCEMENT_TITLE_KEY="thing1",
        WECHAT_ANNOUNCEMENT_CONTENT_KEY="thing2",
        WECHAT_ANNOUNCEMENT_TIME_KEY="time3",
    )
    assert settings.wechat_template("notification") == ("notice-template", "thing1", "thing2", "time3")
