from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.errors import api_error_handler, http_error_handler, integrity_error_handler, unhandled_error_handler, validation_error_handler, ApiError
from app.core.logging import configure_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.logger.info("application_started", environment=get_settings().app_env)
    yield
    await engine.dispose()


logger = configure_logging()
app = FastAPI(title="今天吃什么 API", version="1.0.0", lifespan=lifespan)
app.state.logger = logger
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

settings = get_settings()
if settings.cors_origin_list:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex}"
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info("request_completed", request_id=request_id, method=request.method, path=request.url.path, duration_ms=duration_ms)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")
