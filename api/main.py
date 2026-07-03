"""
Industrial Multi-Agent Ecosystem — FastAPI Application Entry Point.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from config import get_settings
from core.logging_config import setup_logging

# ── Initialize Structured Logging ──────────────────────────────

settings = get_settings()
setup_logging(log_level=settings.log_level)
logger = logging.getLogger(__name__)


# ── Lifespan Context Manager ──────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info(
        "Industrial Multi-Agent Ecosystem starting",
        extra={
            "llm_provider": settings.llm_provider,
            "api_host": settings.api_host,
            "api_port": settings.api_port,
            "log_level": settings.log_level,
        },
    )
    yield
    logger.info("Industrial Multi-Agent Ecosystem shutting down")


# ── FastAPI Application ────────────────────────────────────────

app = FastAPI(
    title="Industrial Multi-Agent Ecosystem",
    description=(
        "Orquestrador Multi-Agente baseado em LlamaIndex Workflows "
        "com ferramentas de Text-to-SQL (CAGED/IBGE), RAG e Previsão."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS Middleware ────────────────────────────────────────────

cors_origins: list[str] = list(settings.cors_origin_list)

for port in ("8501", "8502", "8503", "3000", "8000"):
    for host in ("localhost", "127.0.0.1", "0.0.0.0"):
        cors_origins.append(f"http://{host}:{port}")
        cors_origins.append(f"https://{host}:{port}")

cors_origins = list(dict.fromkeys(cors_origins))

if "*" in settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Global Exception Handler ──────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch all unhandled exceptions and return a structured JSON response."""
    logger.exception(
        "Unhandled exception",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "error_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "detail": f"Ocorreu um erro interno: {exc}",
            "type": type(exc).__name__,
        },
    )


# ── Request Logging Middleware ─────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next: Any,
) -> Any:
    """Log every HTTP request with method, path, status code and duration."""
    start_time: float = time.perf_counter()

    response = await call_next(request)

    duration_ms: float = round((time.perf_counter() - start_time) * 1000, 2)

    path: str = request.url.path
    if path not in ("/api/v1/health", "/docs", "/redoc", "/openapi.json"):
        query_params: dict[str, str] = dict(request.query_params)
        user_agent: str = request.headers.get("user-agent", "unknown")

        logger.info(
            "HTTP request processed",
            extra={
                "event_type": "api_audit",
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": user_agent,
                "query_params": query_params,
            },
        )

    return response


# ── Include Routers ────────────────────────────────────────────

app.include_router(router)


# ── Root Endpoint ──────────────────────────────────────────────


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Return a welcome message with API documentation link."""
    return {
        "service": "Industrial Multi-Agent Ecosystem",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
