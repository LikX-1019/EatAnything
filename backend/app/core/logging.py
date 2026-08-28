import logging

import structlog


def configure_logging() -> structlog.BoundLogger:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    # httpx 的 INFO 日志会包含完整请求 URL，微信接口查询参数中含有敏感凭据。
    logging.getLogger("httpx").setLevel(logging.WARNING)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
    return structlog.get_logger("eat-anything")
