from pydantic import Field

from app.schemas.common import ApiResponse, SchemaBase


class WechatLoginRequest(SchemaBase):
    code: str = Field(min_length=1, max_length=128)


class DevLoginRequest(SchemaBase):
    external_id: str = Field(default="demo-user", min_length=1, max_length=128)


class AdminLoginRequest(SchemaBase):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserSummary(SchemaBase):
    id: str
    nickname: str
    avatar_url: str | None = None


class AdminSummary(SchemaBase):
    id: str
    username: str
    display_name: str
    roles: list[str]


class AuthData(SchemaBase):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserSummary


class AdminAuthData(SchemaBase):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    admin: AdminSummary


AuthResponse = ApiResponse[AuthData]
AdminAuthResponse = ApiResponse[AdminAuthData]
