from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.api.v1.utils import response, school_id as parse_school_id
from app.core.dependencies import SessionDep, UserDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import School
from app.schemas.common import ApiResponse
from app.schemas.users import SchoolSummary, UserProfile
from app.services.users import profile


router = APIRouter(tags=["User"])


@router.get("/me", response_model=ApiResponse[UserProfile])
async def current_user(request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    data = await profile(session, storage, user)
    return {"data": data, "request_id": request.state.request_id}


@router.get("/schools", response_model=ApiResponse[list[SchoolSummary]])
async def list_schools(request: Request, user: UserDep, session: SessionDep):
    schools = list((await session.scalars(select(School).where(School.status == "active").order_by(School.name))).all())
    data = [
        {
            "id": str(school.id),
            "school_code": school.school_code,
            "name": school.name,
            "city": school.city,
            "district": school.district,
            "address": school.address,
        }
        for school in schools
    ]
    return response(request, data)


@router.put("/me/school/{schoolId}", response_model=ApiResponse[UserProfile])
async def select_school(
    schoolId: str,
    request: Request,
    user: UserDep,
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
):
    school_id = parse_school_id(schoolId)
    school = await session.scalar(select(School).where(School.id == school_id, School.status == "active"))
    if school is None:
        raise ApiError(404, "SCHOOL_NOT_FOUND", "学校不存在或已不可用")
    user.school_id = school.id
    await session.commit()
    await session.refresh(user)
    return response(request, await profile(session, storage, user))
