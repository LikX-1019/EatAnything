from functools import lru_cache
from pathlib import Path

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

    postgres_host: str = Field(validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")

    minio_endpoint: str = Field(validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(validation_alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")
    minio_public_url: str = Field(validation_alias="MINIO_PUBLIC_URL")
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
            if self.jwt_secret == "dev-only-change-me-please-set-32-bytes":
                raise ValueError("JWT_SECRET must be changed in production")
            if not self.wechat_app_id or not self.wechat_app_secret:
                raise ValueError("WECHAT_APP_ID and WECHAT_APP_SECRET are required in production")
            if self.dev_auth_enabled:
                raise ValueError("DEV_AUTH_ENABLED must be false in production")
        if self.jwt_expire_seconds <= 0:
            raise ValueError("JWT_EXPIRE_SECONDS must be positive")
        if self.max_upload_bytes <= 0:
            raise ValueError("MAX_UPLOAD_BYTES must be positive")
        return self

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
