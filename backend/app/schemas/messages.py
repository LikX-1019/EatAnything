from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.common import SchemaBase


class MessageItem(SchemaBase):
    id: str
    kind: str
    source: str
    event_type: str | None = None
    title: str
    body_html: str
    priority: str
    action_type: str | None = None
    action_target_id: str | None = None
    publish_at: datetime
    expire_at: datetime | None = None
    is_read: bool = False


class MessageUnreadCount(SchemaBase):
    count: int


class MessageAdminCreate(SchemaBase):
    kind: str = Field(pattern="^(notification|announcement)$")
    title: str = Field(min_length=1, max_length=120)
    body_html: str = Field(min_length=1, max_length=50000)
    target_type: str = Field(pattern="^(all|school|user)$")
    school_id: int | None = Field(default=None, gt=0)
    user_id: int | None = Field(default=None, gt=0)
    priority: str = Field(default="normal", pattern="^(normal|important)$")
    action_type: str | None = None
    action_target_id: int | None = Field(default=None, gt=0)
    wechat_push: bool = False
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    media_ids: list[int] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_target(self):
        if self.target_type == "all" and (self.school_id or self.user_id):
            raise ValueError("全平台消息不能指定学校或用户")
        if self.target_type == "school" and (not self.school_id or self.user_id):
            raise ValueError("学校消息必须且只能指定 schoolId")
        if self.target_type == "user" and (not self.user_id or self.school_id):
            raise ValueError("个人消息必须且只能指定 userId")
        if self.expire_at and self.publish_at and self.expire_at <= self.publish_at:
            raise ValueError("expireAt 必须晚于 publishAt")
        return self


class MessageAdminUpdate(SchemaBase):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body_html: str | None = Field(default=None, min_length=1, max_length=50000)
    target_type: str | None = Field(default=None, pattern="^(all|school|user)$")
    school_id: int | None = Field(default=None, gt=0)
    user_id: int | None = Field(default=None, gt=0)
    priority: str | None = Field(default=None, pattern="^(normal|important)$")
    action_type: str | None = None
    action_target_id: int | None = Field(default=None, gt=0)
    wechat_push: bool | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    media_ids: list[int] | None = Field(default=None, max_length=30)


class WechatConsentRequest(SchemaBase):
    notification: str | None = Field(default=None, pattern="^(accept|reject|ban)$")
    announcement: str | None = Field(default=None, pattern="^(accept|reject|ban)$")


class NotificationSettingsUpdate(SchemaBase):
    wechat_enabled: bool
