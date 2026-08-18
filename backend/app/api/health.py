from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.core.dependencies import SessionDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def live(request: Request):
    return {"data": {"status": "ok"}, "request_id": request.state.request_id}


@router.get("/ready")
async def ready(request: Request, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    try:
        await session.execute(text("SELECT 1"))
        if not await storage.bucket_exists():
            raise RuntimeError("MinIO bucket does not exist")
    except Exception as exc:
        raise ApiError(503, "SERVICE_NOT_READY", "依赖服务尚未就绪") from exc
    return {"data": {"status": "ready", "postgres": "ok", "minio": "ok"}, "request_id": request.state.request_id}
