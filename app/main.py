"""FDE portfolio baseline service.

A minimal but production-shaped FastAPI service: typed config, structured
logging, health/readiness endpoints, and a request-id middleware. This is the
foundation that later weeks extend with RAG and Agent capabilities.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .config import Settings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("fde-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "service_starting",
        extra={"app": settings.app_name, "environment": settings.environment},
    )
    yield
    logger.info("service_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        """Service identity — proves the app is alive and which build is running."""
        return {
            "service": settings.app_name,
            "version": __version__,
            "environment": settings.environment,
        }

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness probe: process is up. Used by Docker/K8s health checks."""
        return {"status": "ok"}

    @app.get("/ready", tags=["meta"])
    async def ready() -> JSONResponse:
        """Readiness probe: dependencies are available. Extended in later weeks
        with vector-store / LLM connectivity checks."""
        return JSONResponse(content={"status": "ready", "dependencies": {}})

    @app.post("/v1/echo", tags=["baseline"])
    async def echo(payload: dict[str, object]) -> dict[str, object]:
        """Baseline typed endpoint; week 2 replaces dict with Pydantic models
        and wires it to an LLM call."""
        return {"received": payload, "count": len(payload)}

    return app


app = create_app()
