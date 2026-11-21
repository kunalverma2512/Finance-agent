import asyncio
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import agent, auth, finance, planning
from app.core.config import get_settings
from app.core.errors import AppError, error_body
from app.core.logging import configure_logging, request_id_var
from app.db.session import get_engine, get_sessionmaker
from app.services.category_data import ensure_system_categories
from app.workers.scheduler import monitoring_loop

log = logging.getLogger("app.request")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    with get_sessionmaker()() as db:
        ensure_system_categories(db)
    task = None
    if s.monitor_interval_minutes > 0:
        task = asyncio.create_task(monitoring_loop(s.monitor_interval_minutes))
    log.info("startup", extra={"environment": s.environment, "llm_enabled": s.llm_enabled})
    yield
    if task:
        task.cancel()
    get_engine().dispose()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Personal Finance Agent", version="1.0.0", lifespan=lifespan,
                  docs_url=None if s.is_production else "/docs",
                  redoc_url=None, openapi_url=None if s.is_production else "/openapi.json")

    if s.cors_origin_list:
        app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=False,
                           allow_methods=["GET", "POST", "PATCH", "DELETE"],
                           allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        started = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            if not request.url.path.startswith(("/docs", "/openapi")):
                response.headers["Content-Security-Policy"] = CSP
            if s.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response
        finally:
            log.info("request", extra={"method": request.method, "path": request.url.path, "status": status,
                                       "duration_ms": int((time.monotonic() - started) * 1000)})
            request_id_var.reset(token)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
                   for e in exc.errors()]  # deliberately omits 'input' (could contain passwords)
        return JSONResponse(error_body("VALIDATION_ERROR", "Request validation failed", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(error_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception):
        log.exception("unhandled_exception")  # details go to logs only, never to the client
        return JSONResponse(error_body("INTERNAL_ERROR", "An unexpected error occurred"), status_code=500)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready():
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            log.exception("readiness_failed")
            return JSONResponse({"status": "unavailable", "checks": {"database": "down"}}, status_code=503)
        return {"status": "ok", "checks": {"database": "ok"}}

    for r in (auth.router, finance.router, planning.router, agent.router):
        app.include_router(r, prefix="/api/v1")

    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
