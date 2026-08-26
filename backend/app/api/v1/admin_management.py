from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import delete, func, or_, select

from app.api.v1.utils import response
from app.core.dependencies import AdminDep, SessionDep, get_minio
from app.core.errors import ApiError
from app.core.security import hash_password
from app.integrations.minio import MinioStorage
from app.models import (
    AdminAuditLog,
    AdminUser,
    AdminUserSchool,
    AppUser,
    CheckIn,
    Review,
    School,
    SchoolArea,
    Store,
    UserFavorite,
    UserRestriction,
)
from app.schemas.common import SchemaBase
from app.services.admin_scope import admin_school_ids, ensure_school_allowed, is_platform_admin, scoped_school_id
from app.services.moderation import add_audit_log, restriction_active


router = APIRouter(prefix="/admin", tags=["Admin Management"])


class SchoolCreate(SchemaBase):
    school_code: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=150)
    city: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=255)
    status: str = Field(default="active", pattern="^(active|hidden)$")


class SchoolUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    city: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|hidden)$")


class AreaCreate(SchemaBase):
    area_code: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0, le=32767)
    status: str = Field(default="active", pattern="^(active|hidden)$")


class AreaUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, ge=0, le=32767)
    status: str | None = Field(default=None, pattern="^(active|hidden)$")


class UserUpdate(SchemaBase):
    school_id: int | None = Field(default=None, gt=0)
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


class RestrictionUpdate(SchemaBase):
    restriction_type: str = Field(pattern="^(comment|image_upload)$")
    blocked: bool
    reason: str = Field(min_length=1, max_length=500)
    blocked_until: datetime | None = None


class BatchAction(SchemaBase):
    ids: list[int] = Field(min_length=1, max_length=100)
    action: str
    reason: str = Field(min_length=1, max_length=500)
    blocked_until: datetime | None = None


class AdminCreate(SchemaBase):
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(platform_admin|school_admin)$")
    school_ids: list[int] = Field(default_factory=list, max_length=50)


class AdminUpdate(SchemaBase):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, pattern="^(platform_admin|school_admin)$")
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    password: str | None = Field(default=None, min_length=8, max_length=128)
    school_ids: list[int] | None = Field(default=None, max_length=50)


def _page(items: list[dict], page: int, page_size: int, total: int) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def _restriction_view(item: UserRestriction | None) -> dict:
    if item is None:
        return {
            "comment_blocked": False,
            "comment_block_reason": None,
            "comment_blocked_until": None,
            "image_upload_blocked": False,
            "image_upload_block_reason": None,
            "image_upload_blocked_until": None,
        }
    return {
        "comment_blocked": restriction_active(item.comment_blocked, item.comment_blocked_until),
        "comment_block_reason": item.comment_block_reason,
        "comment_blocked_until": item.comment_blocked_until,
        "image_upload_blocked": restriction_active(item.image_upload_blocked, item.image_upload_blocked_until),
        "image_upload_block_reason": item.image_upload_block_reason,
        "image_upload_blocked_until": item.image_upload_blocked_until,
    }


@router.get("/me")
async def admin_me(request: Request, admin: AdminDep, session: SessionDep):
    school_ids = await admin_school_ids(session, admin)
    schools = []
    if school_ids:
        rows = list((await session.scalars(select(School).where(School.id.in_(school_ids)).order_by(School.name))).all())
        schools = [{"id": str(item.id), "name": item.name, "school_code": item.school_code} for item in rows]
    return response(
        request,
        {
            "id": str(admin.id),
            "username": admin.username,
            "display_name": admin.display_name,
            "role": admin.role,
            "is_platform_admin": is_platform_admin(admin),
            "schools": schools,
        },
    )


@router.get("/dashboard/summary")
async def dashboard_summary(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    school_id: int | None = Query(default=None, gt=0),
):
    selected = await scoped_school_id(session, admin, school_id)
    school_scope = await admin_school_ids(session, admin)
    school_filters = []
    if selected is not None:
        school_filters = [School.id == selected]
    elif school_scope is not None:
        school_filters = [School.id.in_(school_scope or {-1})]
    school_count = int((await session.scalar(select(func.count(School.id)).where(*school_filters))) or 0)
    store_query = select(func.count(Store.id))
    user_query = select(func.count(AppUser.id))
    review_query = select(func.count(Review.id)).join(Store, Store.id == Review.store_id)
    check_in_query = select(func.count(CheckIn.id))
    if selected is not None:
        store_query = store_query.where(Store.school_id == selected)
        user_query = user_query.where(AppUser.school_id == selected)
        review_query = review_query.where(Store.school_id == selected)
        check_in_query = check_in_query.where(CheckIn.school_id == selected)
    elif school_scope is not None:
        ids = school_scope or {-1}
        store_query = store_query.where(Store.school_id.in_(ids))
        user_query = user_query.where(AppUser.school_id.in_(ids))
        review_query = review_query.where(Store.school_id.in_(ids))
        check_in_query = check_in_query.where(CheckIn.school_id.in_(ids))
    hidden_reviews = review_query.where(Review.status == "hidden")
    hidden_check_ins = check_in_query.where(CheckIn.status == "hidden")
    return response(
        request,
        {
            "school_count": school_count,
            "store_count": int((await session.scalar(store_query)) or 0),
            "user_count": int((await session.scalar(user_query)) or 0),
            "review_count": int((await session.scalar(review_query)) or 0),
            "check_in_count": int((await session.scalar(check_in_query)) or 0),
            "hidden_content_count": int((await session.scalar(hidden_reviews)) or 0)
            + int((await session.scalar(hidden_check_ins)) or 0),
        },
    )


@router.get("/schools")
async def list_admin_schools(request: Request, admin: AdminDep, session: SessionDep):
    scope = await admin_school_ids(session, admin)
    query = select(School).order_by(School.name)
    if scope is not None:
        query = query.where(School.id.in_(scope or {-1}))
    schools = list((await session.scalars(query)).all())
    data = []
    for school in schools:
        areas = list((await session.scalars(select(SchoolArea).where(SchoolArea.school_id == school.id).order_by(SchoolArea.sort_order, SchoolArea.id))).all())
        store_count = int((await session.scalar(select(func.count(Store.id)).where(Store.school_id == school.id))) or 0)
        user_count = int((await session.scalar(select(func.count(AppUser.id)).where(AppUser.school_id == school.id))) or 0)
        data.append(
            {
                "id": str(school.id),
                "school_code": school.school_code,
                "name": school.name,
                "city": school.city,
                "district": school.district,
                "address": school.address,
                "status": school.status,
                "store_count": store_count,
                "user_count": user_count,
                "areas": [
                    {
                        "id": str(area.id),
                        "area_code": area.area_code,
                        "name": area.name,
                        "description": area.description,
                        "sort_order": area.sort_order,
                        "status": area.status,
                    }
                    for area in areas
                ],
            }
        )
    return response(request, data)


@router.post("/schools", status_code=201)
async def create_school(payload: SchoolCreate, request: Request, admin: AdminDep, session: SessionDep):
    if not is_platform_admin(admin):
        raise ApiError(403, "FORBIDDEN", "只有平台管理员可以新增学校")
    code = payload.school_code.strip().lower()
    if await session.scalar(select(School.id).where(School.school_code == code)):
        raise ApiError(409, "SCHOOL_CODE_CONFLICT", "学校编码已存在", field="schoolCode")
    school = School(school_code=code, **payload.model_dump(exclude={"school_code"}))
    session.add(school)
    await session.flush()
    add_audit_log(session, request, admin, action="school.create", target_type="school", target_id=school.id, school_id=school.id, after={"name": school.name, "status": school.status})
    await session.commit()
    return response(request, {"id": str(school.id)})


@router.patch("/schools/{school_id}")
async def update_school(school_id: int, payload: SchoolUpdate, request: Request, admin: AdminDep, session: SessionDep):
    await ensure_school_allowed(session, admin, school_id)
    school = await session.get(School, school_id)
    if school is None:
        raise ApiError(404, "SCHOOL_NOT_FOUND", "学校不存在")
    before = {"name": school.name, "status": school.status}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(school, key, value)
    add_audit_log(session, request, admin, action="school.update", target_type="school", target_id=school.id, school_id=school.id, before=before, after={"name": school.name, "status": school.status})
    await session.commit()
    return response(request, {"id": str(school.id)})


@router.post("/schools/{school_id}/areas", status_code=201)
async def create_area(school_id: int, payload: AreaCreate, request: Request, admin: AdminDep, session: SessionDep):
    await ensure_school_allowed(session, admin, school_id)
    if await session.get(School, school_id) is None:
        raise ApiError(404, "SCHOOL_NOT_FOUND", "学校不存在")
    code = payload.area_code.strip().lower()
    exists = await session.scalar(select(SchoolArea.id).where(SchoolArea.school_id == school_id, SchoolArea.area_code == code))
    if exists:
        raise ApiError(409, "AREA_CODE_CONFLICT", "区域编码已存在", field="areaCode")
    area = SchoolArea(school_id=school_id, area_code=code, **payload.model_dump(exclude={"area_code"}))
    session.add(area)
    await session.flush()
    add_audit_log(session, request, admin, action="area.create", target_type="school_area", target_id=area.id, school_id=school_id, after={"name": area.name, "status": area.status})
    await session.commit()
    return response(request, {"id": str(area.id)})


@router.patch("/school-areas/{area_id}")
async def update_area(area_id: int, payload: AreaUpdate, request: Request, admin: AdminDep, session: SessionDep):
    area = await session.get(SchoolArea, area_id)
    if area is None:
        raise ApiError(404, "AREA_NOT_FOUND", "区域不存在")
    await ensure_school_allowed(session, admin, area.school_id)
    before = {"name": area.name, "status": area.status}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(area, key, value)
    add_audit_log(session, request, admin, action="area.update", target_type="school_area", target_id=area.id, school_id=area.school_id, before=before, after={"name": area.name, "status": area.status})
    await session.commit()
    return response(request, {"id": str(area.id)})


@router.get("/users")
async def list_admin_users(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    school_id: int | None = Query(default=None, gt=0),
    keyword: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, pattern="^(active|disabled)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    selected = await scoped_school_id(session, admin, school_id)
    scope = await admin_school_ids(session, admin)
    filters = []
    if selected is not None:
        filters.append(AppUser.school_id == selected)
    elif scope is not None:
        filters.append(AppUser.school_id.in_(scope or {-1}))
    if status:
        filters.append(AppUser.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(AppUser.nickname.ilike(pattern), AppUser.external_id.ilike(pattern)))
    total = int((await session.scalar(select(func.count(AppUser.id)).where(*filters))) or 0)
    users = list((await session.scalars(select(AppUser).where(*filters).order_by(AppUser.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    data = []
    for user in users:
        restriction = await session.get(UserRestriction, user.id)
        review_count = int((await session.scalar(select(func.count(Review.id)).where(Review.user_id == user.id))) or 0)
        check_in_count = int((await session.scalar(select(func.count(CheckIn.id)).where(CheckIn.user_id == user.id))) or 0)
        data.append(
            {
                "id": str(user.id),
                "external_id": user.external_id,
                "nickname": user.nickname,
                "school_id": str(user.school_id) if user.school_id else None,
                "school_name": user.school.name if user.school else None,
                "level": user.level,
                "status": user.status,
                "review_count": review_count,
                "check_in_count": check_in_count,
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
                "restriction": _restriction_view(restriction),
            }
        )
    return response(request, _page(data, page, page_size, total))


@router.get("/users/{user_id}")
async def get_admin_user(user_id: int, request: Request, admin: AdminDep, session: SessionDep):
    user = await session.get(AppUser, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
    if user.school_id:
        await ensure_school_allowed(session, admin, user.school_id)
    reviews = list((await session.scalars(select(Review).where(Review.user_id == user.id).order_by(Review.created_at.desc()))).all())
    check_ins = list((await session.scalars(select(CheckIn).where(CheckIn.user_id == user.id).order_by(CheckIn.checked_at.desc()))).all())
    favorite_count = int((await session.scalar(select(func.count(UserFavorite.store_id)).where(UserFavorite.user_id == user.id))) or 0)
    return response(
        request,
        {
            "id": str(user.id),
            "external_id": user.external_id,
            "nickname": user.nickname,
            "school_id": str(user.school_id) if user.school_id else None,
            "school_name": user.school.name if user.school else None,
            "status": user.status,
            "level": user.level,
            "slogan": user.slogan,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "restriction": _restriction_view(await session.get(UserRestriction, user.id)),
            "stats": {"favorite_count": favorite_count, "review_count": len(reviews), "check_in_count": len(check_ins)},
            "reviews": [{"id": str(item.id), "content": item.content, "rating": item.rating, "status": item.status, "moderation_reason": item.moderation_reason, "store_id": str(item.store_id), "store_name": item.store.name, "created_at": item.created_at} for item in reviews],
            "check_ins": [{"id": str(item.id), "store_id": str(item.store_id), "store_name": item.store.name, "photo_url": f"/api/v1/admin/check-ins/{item.id}/photo", "note": item.note, "status": item.status, "moderation_reason": item.moderation_reason, "checked_at": item.checked_at} for item in check_ins],
        },
    )


@router.patch("/users/{user_id}")
async def update_admin_user(user_id: int, payload: UserUpdate, request: Request, admin: AdminDep, session: SessionDep):
    user = await session.get(AppUser, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
    if user.school_id:
        await ensure_school_allowed(session, admin, user.school_id)
    if payload.school_id:
        await ensure_school_allowed(session, admin, payload.school_id)
    before = {"schoolId": user.school_id, "status": user.status}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    add_audit_log(session, request, admin, action="user.update", target_type="user", target_id=user.id, school_id=user.school_id, before=before, after={"schoolId": user.school_id, "status": user.status})
    await session.commit()
    return response(request, {"id": str(user.id)})


async def _set_restriction(session: SessionDep, admin: AdminUser, user: AppUser, payload: RestrictionUpdate) -> UserRestriction:
    item = await session.get(UserRestriction, user.id)
    if item is None:
        item = UserRestriction(user_id=user.id)
        session.add(item)
    prefix = "comment" if payload.restriction_type == "comment" else "image_upload"
    setattr(item, f"{prefix}_blocked", payload.blocked)
    setattr(item, f"{prefix}_block_reason", payload.reason.strip())
    setattr(item, f"{prefix}_blocked_until", payload.blocked_until if payload.blocked else None)
    item.updated_by = admin.id
    item.updated_at = datetime.now(UTC)
    return item


@router.post("/users/{user_id}/restrictions")
async def update_user_restriction(user_id: int, payload: RestrictionUpdate, request: Request, admin: AdminDep, session: SessionDep):
    user = await session.get(AppUser, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
    if user.school_id:
        await ensure_school_allowed(session, admin, user.school_id)
    item = await _set_restriction(session, admin, user, payload)
    add_audit_log(session, request, admin, action=f"user.restriction.{payload.restriction_type}", target_type="user", target_id=user.id, school_id=user.school_id, reason=payload.reason, after=_restriction_view(item))
    await session.commit()
    return response(request, _restriction_view(item))


@router.post("/users/batch-action")
async def batch_user_action(payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    users = list((await session.scalars(select(AppUser).where(AppUser.id.in_(payload.ids)).with_for_update())).all())
    if len(users) != len(set(payload.ids)):
        raise ApiError(404, "USER_NOT_FOUND", "部分用户不存在")
    for user in users:
        if user.school_id:
            await ensure_school_allowed(session, admin, user.school_id)
        if payload.action in {"enable", "disable"}:
            user.status = "active" if payload.action == "enable" else "disabled"
        elif payload.action in {"block_comment", "unblock_comment", "block_image", "unblock_image"}:
            is_comment = "comment" in payload.action
            await _set_restriction(
                session,
                admin,
                user,
                RestrictionUpdate(
                    restriction_type="comment" if is_comment else "image_upload",
                    blocked=payload.action.startswith("block_"),
                    reason=payload.reason,
                    blocked_until=payload.blocked_until,
                ),
            )
        else:
            raise ApiError(400, "INVALID_ARGUMENT", "不支持的批量操作", field="action")
        add_audit_log(session, request, admin, action=f"user.batch.{payload.action}", target_type="user", target_id=user.id, school_id=user.school_id, reason=payload.reason)
    await session.commit()
    return response(request, {"affected_count": len(users)})


@router.get("/reviews")
async def list_admin_reviews(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    school_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    user_id: int | None = Query(default=None, gt=0),
    keyword: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, pattern="^(published|hidden)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    selected = await scoped_school_id(session, admin, school_id)
    scope = await admin_school_ids(session, admin)
    filters = []
    if selected is not None:
        filters.append(Store.school_id == selected)
    elif scope is not None:
        filters.append(Store.school_id.in_(scope or {-1}))
    if store_id:
        filters.append(Review.store_id == store_id)
    if user_id:
        filters.append(Review.user_id == user_id)
    if status:
        filters.append(Review.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Review.content.ilike(pattern), AppUser.nickname.ilike(pattern), Store.name.ilike(pattern)))
    base = select(Review, Store, AppUser).join(Store, Store.id == Review.store_id).join(AppUser, AppUser.id == Review.user_id).where(*filters)
    total = int((await session.scalar(select(func.count()).select_from(base.subquery()))) or 0)
    rows = (await session.execute(base.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = [
        {
            "id": str(review.id),
            "content": review.content,
            "rating": review.rating,
            "status": review.status,
            "moderation_reason": review.moderation_reason,
            "user": {"id": str(user.id), "nickname": user.nickname},
            "store": {"id": str(store.id), "name": store.name, "school_id": str(store.school_id), "school_name": store.school.name},
            "created_at": review.created_at,
            "moderated_at": review.moderated_at,
        }
        for review, store, user in rows
    ]
    return response(request, _page(items, page, page_size, total))


async def _moderate_reviews(ids: list[int], action: str, reason: str, request: Request, admin: AdminUser, session: SessionDep) -> int:
    if action not in {"hide", "restore"}:
        raise ApiError(400, "INVALID_ARGUMENT", "评论操作必须为 hide 或 restore")
    rows = list((await session.scalars(select(Review).where(Review.id.in_(ids)).with_for_update())).all())
    if len(rows) != len(set(ids)):
        raise ApiError(404, "REVIEW_NOT_FOUND", "部分评论不存在")
    for item in rows:
        await ensure_school_allowed(session, admin, item.store.school_id)
        before = {"status": item.status}
        item.status = "hidden" if action == "hide" else "published"
        item.moderation_reason = reason if action == "hide" else None
        item.moderated_by = admin.id
        item.moderated_at = datetime.now(UTC)
        add_audit_log(session, request, admin, action=f"review.{action}", target_type="review", target_id=item.id, school_id=item.store.school_id, reason=reason, before=before, after={"status": item.status})
    await session.commit()
    return len(rows)


@router.post("/reviews/{review_id}/hide")
async def hide_review(review_id: int, payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    count = await _moderate_reviews([review_id], "hide", payload.reason, request, admin, session)
    return response(request, {"affected_count": count})


@router.post("/reviews/{review_id}/restore")
async def restore_review(review_id: int, payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    count = await _moderate_reviews([review_id], "restore", payload.reason, request, admin, session)
    return response(request, {"affected_count": count})


@router.post("/reviews/batch-action")
async def batch_review_action(payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    count = await _moderate_reviews(payload.ids, payload.action, payload.reason, request, admin, session)
    return response(request, {"affected_count": count})


@router.get("/check-ins")
async def list_admin_check_ins(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    school_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    user_id: int | None = Query(default=None, gt=0),
    status: str | None = Query(default=None, pattern="^(published|hidden)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    selected = await scoped_school_id(session, admin, school_id)
    scope = await admin_school_ids(session, admin)
    filters = []
    if selected is not None:
        filters.append(CheckIn.school_id == selected)
    elif scope is not None:
        filters.append(CheckIn.school_id.in_(scope or {-1}))
    if store_id:
        filters.append(CheckIn.store_id == store_id)
    if user_id:
        filters.append(CheckIn.user_id == user_id)
    if status:
        filters.append(CheckIn.status == status)
    total = int((await session.scalar(select(func.count(CheckIn.id)).where(*filters))) or 0)
    rows = list((await session.scalars(select(CheckIn).where(*filters).order_by(CheckIn.checked_at.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    items = [
        {
            "id": str(item.id),
            "photo_url": f"/api/v1/admin/check-ins/{item.id}/photo",
            "note": item.note,
            "status": item.status,
            "moderation_reason": item.moderation_reason,
            "user": {"id": str(item.user.id), "nickname": item.user.nickname},
            "store": {"id": str(item.store.id), "name": item.store.name},
            "school_id": str(item.school_id),
            "school_name": item.store.school.name,
            "checked_at": item.checked_at,
            "moderated_at": item.moderated_at,
        }
        for item in rows
    ]
    return response(request, _page(items, page, page_size, total))


@router.get("/check-ins/{check_in_id}/photo")
async def admin_check_in_photo(check_in_id: int, admin: AdminDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    item = await session.get(CheckIn, check_in_id)
    if item is None:
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡记录不存在")
    await ensure_school_allowed(session, admin, item.school_id)
    try:
        content, content_type = await storage.get_bytes(item.photo.object_key, bucket=storage.private_bucket)
    except Exception as exc:
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡照片不存在") from exc
    return Response(content=content, media_type=content_type or "application/octet-stream", headers={"Cache-Control": "private, max-age=60"})


async def _moderate_check_ins(ids: list[int], action: str, reason: str, request: Request, admin: AdminUser, session: SessionDep) -> int:
    if action not in {"hide", "restore"}:
        raise ApiError(400, "INVALID_ARGUMENT", "打卡操作必须为 hide 或 restore")
    rows = list((await session.scalars(select(CheckIn).where(CheckIn.id.in_(ids)).with_for_update())).all())
    if len(rows) != len(set(ids)):
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "部分打卡记录不存在")
    for item in rows:
        await ensure_school_allowed(session, admin, item.school_id)
        before = {"status": item.status}
        item.status = "hidden" if action == "hide" else "published"
        item.moderation_reason = reason if action == "hide" else None
        item.moderated_by = admin.id
        item.moderated_at = datetime.now(UTC)
        add_audit_log(session, request, admin, action=f"check_in.{action}", target_type="check_in", target_id=item.id, school_id=item.school_id, reason=reason, before=before, after={"status": item.status})
    await session.commit()
    return len(rows)


@router.post("/check-ins/{check_in_id}/hide")
async def hide_check_in(check_in_id: int, payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    count = await _moderate_check_ins([check_in_id], "hide", payload.reason, request, admin, session)
    return response(request, {"affected_count": count})


@router.post("/check-ins/{check_in_id}/restore")
async def restore_check_in(check_in_id: int, payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    count = await _moderate_check_ins([check_in_id], "restore", payload.reason, request, admin, session)
    return response(request, {"affected_count": count})


@router.post("/check-ins/batch-action")
async def batch_check_in_action(payload: BatchAction, request: Request, admin: AdminDep, session: SessionDep):
    count = await _moderate_check_ins(payload.ids, payload.action, payload.reason, request, admin, session)
    return response(request, {"affected_count": count})


@router.get("/admin-users")
async def list_admin_accounts(request: Request, admin: AdminDep, session: SessionDep):
    if not is_platform_admin(admin):
        raise ApiError(403, "FORBIDDEN", "只有平台管理员可以管理管理员账号")
    rows = list((await session.scalars(select(AdminUser).order_by(AdminUser.created_at.desc()))).all())
    data = []
    for item in rows:
        school_ids = list((await session.scalars(select(AdminUserSchool.school_id).where(AdminUserSchool.admin_user_id == item.id))).all())
        data.append({"id": str(item.id), "username": item.username, "display_name": item.display_name, "role": item.role, "status": item.status, "school_ids": [str(value) for value in school_ids], "last_login_at": item.last_login_at, "created_at": item.created_at})
    return response(request, data)


@router.post("/admin-users", status_code=201)
async def create_admin_account(payload: AdminCreate, request: Request, admin: AdminDep, session: SessionDep):
    if not is_platform_admin(admin):
        raise ApiError(403, "FORBIDDEN", "只有平台管理员可以新增管理员")
    username = payload.username.strip()
    if await session.scalar(select(AdminUser.id).where(AdminUser.username == username)):
        raise ApiError(409, "ADMIN_USERNAME_CONFLICT", "管理员账号已存在")
    if payload.role == "school_admin" and not payload.school_ids:
        raise ApiError(422, "SCHOOL_SCOPE_REQUIRED", "学校管理员至少绑定一所学校")
    item = AdminUser(username=username, password_hash=hash_password(payload.password), display_name=payload.display_name.strip(), role=payload.role, status="active")
    session.add(item)
    await session.flush()
    for school_id in set(payload.school_ids if payload.role == "school_admin" else []):
        if await session.get(School, school_id) is None:
            raise ApiError(404, "SCHOOL_NOT_FOUND", "绑定的学校不存在")
        session.add(AdminUserSchool(admin_user_id=item.id, school_id=school_id))
    add_audit_log(session, request, admin, action="admin.create", target_type="admin_user", target_id=item.id, after={"role": item.role, "status": item.status})
    await session.commit()
    return response(request, {"id": str(item.id)})


@router.patch("/admin-users/{admin_id}")
async def update_admin_account(admin_id: int, payload: AdminUpdate, request: Request, admin: AdminDep, session: SessionDep):
    if not is_platform_admin(admin):
        raise ApiError(403, "FORBIDDEN", "只有平台管理员可以修改管理员")
    item = await session.get(AdminUser, admin_id)
    if item is None:
        raise ApiError(404, "ADMIN_NOT_FOUND", "管理员不存在")
    before = {"role": item.role, "status": item.status}
    values = payload.model_dump(exclude_unset=True, exclude={"school_ids", "password"})
    for key, value in values.items():
        setattr(item, key, value)
    if payload.password:
        item.password_hash = hash_password(payload.password)
    if payload.school_ids is not None or payload.role is not None:
        await session.execute(delete(AdminUserSchool).where(AdminUserSchool.admin_user_id == item.id))
        school_ids = payload.school_ids or []
        if item.role == "school_admin" and not school_ids:
            raise ApiError(422, "SCHOOL_SCOPE_REQUIRED", "学校管理员至少绑定一所学校")
        for school_id in set(school_ids if item.role == "school_admin" else []):
            if await session.get(School, school_id) is None:
                raise ApiError(404, "SCHOOL_NOT_FOUND", "绑定的学校不存在")
            session.add(AdminUserSchool(admin_user_id=item.id, school_id=school_id))
    add_audit_log(session, request, admin, action="admin.update", target_type="admin_user", target_id=item.id, before=before, after={"role": item.role, "status": item.status})
    await session.commit()
    return response(request, {"id": str(item.id)})


@router.get("/audit-logs")
async def list_audit_logs(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    school_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    selected = await scoped_school_id(session, admin, school_id)
    scope = await admin_school_ids(session, admin)
    filters = []
    if selected is not None:
        filters.append(AdminAuditLog.school_id == selected)
    elif scope is not None:
        filters.append(AdminAuditLog.school_id.in_(scope or {-1}))
    if action:
        filters.append(AdminAuditLog.action == action)
    total = int((await session.scalar(select(func.count(AdminAuditLog.id)).where(*filters))) or 0)
    rows = list((await session.scalars(select(AdminAuditLog).where(*filters).order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    items = []
    for item in rows:
        operator = await session.get(AdminUser, item.admin_user_id) if item.admin_user_id else None
        school = await session.get(School, item.school_id) if item.school_id else None
        items.append({"id": str(item.id), "operator": operator.display_name if operator else "已删除管理员", "school_name": school.name if school else None, "action": item.action, "target_type": item.target_type, "target_id": item.target_id, "reason": item.reason, "ip_address": item.ip_address, "created_at": item.created_at})
    return response(request, _page(items, page, page_size, total))
