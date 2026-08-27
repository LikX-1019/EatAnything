from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.core.dependencies import SessionDep, SettingsDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.core.metrics import metrics


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def live(request: Request):
    return {"data": {"status": "ok"}, "request_id": request.state.request_id}


@router.get("/ready")
async def ready(request: Request, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    try:
        await session.execute(text("SELECT 1"))
        if not await storage.bucket_exists() or not await storage.bucket_exists(storage.private_bucket):
            raise RuntimeError("MinIO public/private bucket does not exist")
    except Exception as exc:
        raise ApiError(503, "SERVICE_NOT_READY", "依赖服务尚未就绪") from exc
    return {"data": {"status": "ready", "postgres": "ok", "minio": "ok"}, "request_id": request.state.request_id}


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def metrics_endpoint(request: Request, settings: SettingsDep):
    if not settings.metrics_enabled:
        raise ApiError(404, "NOT_FOUND", "指标未启用")
    if settings.metrics_token and request.headers.get("X-Metrics-Token") != settings.metrics_token:
        raise ApiError(404, "NOT_FOUND", "指标未启用")
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")
