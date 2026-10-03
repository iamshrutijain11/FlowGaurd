import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.document_service import upload_root

logger = logging.getLogger("flowguard")

_HTTP_CODES = {
    401: "NOT_AUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
    413: "FILE_TOO_LARGE", 415: "UNSUPPORTED_FILE_TYPE",
}


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upload_root()
    if settings.AUTO_CREATE_TABLES:
        import app.models  # noqa: F401  (register tables)

        Base.metadata.create_all(engine)
    if settings.SEED_DEMO_DATA:
        from app.db.seed import seed_demo_data

        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "FlowGuard - investor grievance tracking. Single source of truth for grievances, events, "
        "documents and notifications. All responses use `{success, data, message}` / "
        "`{success:false, error:{code,message}}`."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return _error(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    return _error(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in err["loc"][1:]) or str(err["loc"][0]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return _error(422, "VALIDATION_ERROR", "Request validation failed", details)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return _error(500, "INTERNAL_ERROR", "Something went wrong. Please try again.")


@app.get(
    "/health", tags=["Health"], summary="Health check",
    description="Liveness probe.", response_description='{"status": "ok"}',
)
def health():
    return {"status": "ok"}


app.include_router(api_router)
