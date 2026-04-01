import re

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()

_SECRET_PATTERN = re.compile(
    r"(password|passwd|api[_-]?key|secret|token|bearer|authorization"
    r"|database_url|db_url|dsn|credential)[\s:=]+\S+",
    re.IGNORECASE,
)


def _sanitize_for_log(text: str) -> str:
    return _SECRET_PATTERN.sub(r"\1=***REDACTED***", str(text))


async def error_handler_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        request_id = getattr(request.state, "request_id", "unknown")
        await logger.aerror(
            "unhandled_exception",
            request_id=request_id,
            error=_sanitize_for_log(str(exc)),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred. Please try again later.",
                "instance": request.url.path,
            },
        )
