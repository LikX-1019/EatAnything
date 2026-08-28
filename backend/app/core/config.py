from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_timezone: str = Field(default="Asia/Shanghai", validation_alias="APP_TIMEZONE")
    jwt_secret: str = Field(default="dev-only-change-me-please-set-32-bytes", validation_alias="JWT_SECRET")
    jwt_expire_seconds: int = Field(default=60 * 60 * 24 * 7, validation_alias="JWT_EXPIRE_SECONDS")
    dev_auth_enabled: bool = Field(default=False, validation_alias="DEV_AUTH_ENABLED")
    wechat_app_id: str | None = Field(default=None, validation_alias="WECHAT_APP_ID")
    wechat_app_secret: str | None = Field(default=None, validation_alias="WECHAT_APP_SECRET")
    wechat_subscribe_enabled: bool = Field(default=False, validation_alias="WECHAT_SUBSCRIBE_ENABLED")
    wechat_notification_template_id: str | None = Field(default=None, validation_alias="WECHAT_NOTIFICATION_TEMPLATE_ID")
    wechat_notification_title_key: str | None = Field(default=None, validation_alias="WECHAT_NOTIFICATION_TITLE_KEY")
    wechat_notification_content_key: str | None = Field(default=None, validation_alias="WECHAT_NOTIFICATION_CONTENT_KEY")
    wechat_notification_time_key: str | None = Field(default=None, validation_alias="WECHAT_NOTIFICATION_TIME_KEY")
    wechat_announcement_template_id: str | None = Field(default=None, validation_alias="WECHAT_ANNOUNCEMENT_TEMPLATE_ID")
    wechat_announcement_title_key: str | None = Field(default=None, validation_alias="WECHAT_ANNOUNCEMENT_TITLE_KEY")
    wechat_announcement_content_key: str | None = Field(default=None, validation_alias="WECHAT_ANNOUNCEMENT_CONTENT_KEY")
    wechat_announcement_time_key: str | None = Field(default=None, validation_alias="WECHAT_ANNOUNCEMENT_TIME_KEY")

    postgres_host: str = Field(validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")

    minio_endpoint: str = Field(validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(validation_alias="MINIO_BUCKET")
    minio_private_bucket: str = Field(default="eat-anything-private", validation_alias="MINIO_PRIVATE_BUCKET")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")
    minio_public_url: str = Field(validation_alias="MINIO_PUBLIC_URL")
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")
    seed_admin_password: str | None = Field(default=None, validation_alias="SEED_ADMIN_PASSWORD")
    metrics_enabled: bool = Field(default=True, validation_alias="METRICS_ENABLED")
    metrics_token: str | None = Field(default=None, validation_alias="METRICS_TOKEN")
    trusted_proxy_ips: str = Field(default="", validation_alias="TRUSTED_PROXY_IPS")
    weather_provider: str = Field(default="open_meteo", validation_alias="WEATHER_PROVIDER")
    open_meteo_api_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        validation_alias="OPEN_METEO_API_URL",
    )
    qweather_api_host: str | None = Field(default=None, validation_alias="QWEATHER_API_HOST")
    qweather_api_key: str | None = Field(default=None, validation_alias="QWEATHER_API_KEY")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_origins(cls, value: str | list[str] | None) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        return str(value)

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"}:
            self._validate_production_secret("JWT_SECRET", self.jwt_secret, minimum_length=32)
            self._validate_production_secret("POSTGRES_PASSWORD", self.postgres_password, minimum_length=16)
            self._validate_production_secret("MINIO_ACCESS_KEY", self.minio_access_key, minimum_length=12)
            self._validate_production_secret("MINIO_SECRET_KEY", self.minio_secret_key, minimum_length=16)
            if not self.wechat_app_id or not self.wechat_app_secret:
                raise ValueError("WECHAT_APP_ID and WECHAT_APP_SECRET are required in production")
            if self.dev_auth_enabled:
                raise ValueError("DEV_AUTH_ENABLED must be false in production")
            self._validate_public_url("MINIO_PUBLIC_URL", self.minio_public_url)
            if not self.minio_private_bucket or self.minio_private_bucket == self.minio_bucket:
                raise ValueError("MINIO_PRIVATE_BUCKET must be configured and differ from MINIO_BUCKET")
            if self.metrics_enabled and not self.metrics_token:
                raise ValueError("METRICS_TOKEN is required when METRICS_ENABLED is true in production")
            if self.metrics_enabled and self.metrics_token:
                self._validate_production_secret("METRICS_TOKEN", self.metrics_token, minimum_length=16)
            for origin in self.cors_origin_list:
                self._validate_public_url("CORS_ORIGINS", origin)
        if self.jwt_expire_seconds <= 0:
            raise ValueError("JWT_EXPIRE_SECONDS must be positive")
        if self.max_upload_bytes <= 0:
            raise ValueError("MAX_UPLOAD_BYTES must be positive")
        if self.wechat_subscribe_enabled:
            required = {
                "WECHAT_APP_ID": self.wechat_app_id,
                "WECHAT_APP_SECRET": self.wechat_app_secret,
                "WECHAT_NOTIFICATION_TEMPLATE_ID": self.wechat_notification_template_id,
                "WECHAT_NOTIFICATION_TITLE_KEY": self.wechat_notification_title_key,
                "WECHAT_NOTIFICATION_CONTENT_KEY": self.wechat_notification_content_key,
                "WECHAT_NOTIFICATION_TIME_KEY": self.wechat_notification_time_key,
                "WECHAT_ANNOUNCEMENT_TEMPLATE_ID": self.wechat_announcement_template_id,
                "WECHAT_ANNOUNCEMENT_TITLE_KEY": self.wechat_announcement_title_key,
                "WECHAT_ANNOUNCEMENT_CONTENT_KEY": self.wechat_announcement_content_key,
                "WECHAT_ANNOUNCEMENT_TIME_KEY": self.wechat_announcement_time_key,
            }
            missing = [name for name, value in required.items() if not value or not value.strip()]
            if missing:
                raise ValueError(f"微信订阅消息已启用，但缺少配置：{', '.join(missing)}")
        self.weather_provider = self.weather_provider.strip().lower()
        if self.weather_provider not in {"open_meteo", "qweather"}:
            raise ValueError("WEATHER_PROVIDER 只允许 open_meteo 或 qweather")
        if self.weather_provider == "qweather":
            missing_weather = [
                name
                for name, value in {
                    "QWEATHER_API_HOST": self.qweather_api_host,
                    "QWEATHER_API_KEY": self.qweather_api_key,
                }.items()
                if not value or not value.strip()
            ]
            if missing_weather:
                raise ValueError(f"和风天气已启用，但缺少配置：{', '.join(missing_weather)}")
            self._validate_weather_host(self.qweather_api_host or "")
        return self

    @staticmethod
    def _validate_weather_host(value: str) -> None:
        parsed = urlparse(value.strip() if "://" in value else f"https://{value.strip()}")
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("QWEATHER_API_HOST 必须是有效的 HTTPS 专属 Host")

    def wechat_template(self, kind: str) -> tuple[str, str, str, str] | None:
        values = (
            self.wechat_notification_template_id,
            self.wechat_notification_title_key,
            self.wechat_notification_content_key,
            self.wechat_notification_time_key,
        ) if kind == "notification" else (
            self.wechat_announcement_template_id,
            self.wechat_announcement_title_key,
            self.wechat_announcement_content_key,
            self.wechat_announcement_time_key,
        )
        return tuple(str(value) for value in values) if all(values) else None

    @staticmethod
    def _validate_production_secret(name: str, value: str, *, minimum_length: int) -> None:
        normalized = value.strip().lower()
        forbidden = ("change-me", "changeme", "example", "your_", "dev-only", "password")
        if len(value.strip()) < minimum_length or any(marker in normalized for marker in forbidden):
            raise ValueError(f"{name} must be a strong non-template value in production")

    @staticmethod
    def _validate_public_url(name: str, value: str) -> None:
        parsed = urlparse(value.strip())
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise ValueError(f"{name} must be an absolute HTTP(S) URL in production")
        blocked = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "121.43.97.186"}
        if hostname in blocked or hostname == "example.com" or hostname.endswith(".example.com") or hostname.endswith(".example.test"):
            raise ValueError(f"{name} must not point to a local, test, or placeholder host in production")

    @property
    def database_url(self) -> str:
        from sqlalchemy.engine import URL

        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
