from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


store_category_links = Table(
    "store_category_links",
    Base.metadata,
    Column("store_id", BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", SmallInteger, ForeignKey("store_categories.id", ondelete="RESTRICT"), primary_key=True),
)


class MediaObject(Base):
    __tablename__ = "media_objects"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    bucket: Mapped[str] = mapped_column(String(128))
    object_key: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    source_provider: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text)
    license_name: Mapped[str | None] = mapped_column(String(128))
    license_url: Mapped[str | None] = mapped_column(Text)
    attribution_text: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    purpose: Mapped[str] = mapped_column(String(30), server_default=text("'system'"))
    upload_state: Mapped[str] = mapped_column(String(20), server_default=text("'attached'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class AppUser(Base):
    __tablename__ = "app_users"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id", ondelete="SET NULL"))
    nickname: Mapped[str] = mapped_column(String(80))
    avatar_media_id: Mapped[int | None] = mapped_column(ForeignKey("media_objects.id", ondelete="SET NULL"))
    slogan: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(20))
    birthday: Mapped[date | None] = mapped_column(Date)
    level: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    school: Mapped[School | None] = relationship(lazy="joined")
    avatar: Mapped[MediaObject | None] = relationship(foreign_keys=[avatar_media_id])


class StoreCategory(Base):
    __tablename__ = "store_categories"
    id: Mapped[int] = mapped_column(SmallInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class School(Base):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    city: Mapped[str | None] = mapped_column(String(60))
    district: Mapped[str | None] = mapped_column(String(60))
    address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class SchoolArea(Base):
    __tablename__ = "school_areas"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False)
    area_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    school: Mapped[School] = relationship(lazy="joined")


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        ForeignKeyConstraint(
            ["school_id", "area_id"],
            ["school_areas.school_id", "school_areas.id"],
            name="fk_stores_school_area",
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    store_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False)
    area_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(60))
    district: Mapped[str | None] = mapped_column(String(60))
    address: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    phone: Mapped[str | None] = mapped_column(String(40))
    business_hours: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    school: Mapped[School] = relationship(lazy="joined", foreign_keys=[school_id], overlaps="area")
    area: Mapped[SchoolArea] = relationship(
        lazy="joined",
        foreign_keys=[school_id, area_id],
        overlaps="school",
    )
    categories: Mapped[list[StoreCategory]] = relationship(secondary=store_category_links, lazy="selectin")
    images: Mapped[list[StoreImage]] = relationship(back_populates="store", lazy="selectin", cascade="all, delete-orphan")


class StoreImage(Base):
    __tablename__ = "store_images"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    media_id: Mapped[int] = mapped_column(ForeignKey("media_objects.id", ondelete="RESTRICT"))
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    store: Mapped[Store] = relationship(back_populates="images")
    media: Mapped[MediaObject] = relationship(lazy="joined")


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class CheckIn(Base):
    __tablename__ = "check_ins"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="RESTRICT"))
    photo_media_id: Mapped[int] = mapped_column(ForeignKey("media_objects.id", ondelete="RESTRICT"), unique=True)
    note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'published'"))
    moderation_reason: Mapped[str | None] = mapped_column(String(500))
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    user: Mapped[AppUser] = relationship(lazy="joined")
    store: Mapped[Store] = relationship(lazy="joined")
    photo: Mapped[MediaObject] = relationship(lazy="joined")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    check_in_id: Mapped[int | None] = mapped_column(ForeignKey("check_ins.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    content: Mapped[str] = mapped_column(Text)
    visited_at: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'published'"))
    moderation_reason: Mapped[str | None] = mapped_column(String(500))
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    user: Mapped[AppUser] = relationship(lazy="joined")
    store: Mapped[Store] = relationship(lazy="joined")
    check_in: Mapped[CheckIn | None] = relationship(lazy="joined")


class ActivityHistory(Base):
    __tablename__ = "activity_history"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    store: Mapped[Store] = relationship(lazy="joined")


class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(50), server_default=text("'store_admin'"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class AdminUserSchool(Base):
    __tablename__ = "admin_user_schools"
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class UserRestriction(Base):
    __tablename__ = "user_restrictions"
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    comment_blocked: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    comment_block_reason: Mapped[str | None] = mapped_column(String(500))
    comment_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    image_upload_blocked: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    image_upload_block_reason: Mapped[str | None] = mapped_column(String(500))
    image_upload_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(String(500))
    before_data: Mapped[dict | None] = mapped_column(JSONB)
    after_data: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class PlatformMessage(Base):
    __tablename__ = "platform_messages"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'admin'"))
    event_type: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'normal'"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'draft'"))
    action_type: Mapped[str | None] = mapped_column(String(30))
    action_target_id: Mapped[int | None] = mapped_column(BigInteger)
    wechat_push: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatch_prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class MessageMediaLink(Base):
    __tablename__ = "message_media_links"
    message_id: Mapped[int] = mapped_column(ForeignKey("platform_messages.id", ondelete="CASCADE"), primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_objects.id", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class MessageReadState(Base):
    __tablename__ = "message_read_states"
    message_id: Mapped[int] = mapped_column(ForeignKey("platform_messages.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class UserWechatSubscription(Base):
    __tablename__ = "user_wechat_subscriptions"
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), primary_key=True)
    template_kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'unknown'"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class WechatDeliveryJob(Base):
    __tablename__ = "wechat_delivery_jobs"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_wechat_delivery_message_user"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("platform_messages.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False)
    template_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
