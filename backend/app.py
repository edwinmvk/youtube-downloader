from __future__ import annotations

import logging
import os
import shutil
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes.convert import convert_router
from routes.audio import audio_router
from routes.download import download_router
from routes.health import health_router
from services.ffmpeg_service import FFmpegNotAvailableError
from services.job_service import job_manager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _max_file_size_bytes() -> int:
    raw = os.getenv("MAX_FILE_SIZE_MB", "500")
    try:
        size_mb = int(raw)
        if size_mb <= 0:
            raise ValueError
    except ValueError:
        logger.warning("Invalid MAX_FILE_SIZE_MB=%r. Falling back to 500 MB.", raw)
        size_mb = 500
    return size_mb * 1024 * 1024


class RequestTooLargeError(Exception):
    """Raised when an incoming HTTP request exceeds the configured body limit."""


class MaxBodySizeMiddleware:
    """Reject requests larger than the configured body size without buffering them."""

    def __init__(self, app: ASGIApp, max_body_size: int) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")

        if content_length is not None:
            try:
                if int(content_length) > self.max_body_size:
                    response = JSONResponse(
                        {"error": "File is too large."},
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        bytes_received = 0

        async def limited_receive() -> Message:
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > self.max_body_size:
                    raise RequestTooLargeError()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            response = JSONResponse(
                {"error": "File is too large."},
                status_code=413,
            )
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    job_manager.shutdown()


def create_app() -> FastAPI:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
    max_content_length = _max_file_size_bytes()

    app = FastAPI(
        title="YouTube Downloader Backend",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(MaxBodySizeMiddleware, max_body_size=max_content_length)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Download-Filename"],
    )

    app.include_router(health_router)
    app.include_router(download_router)
    app.include_router(convert_router)
    app.include_router(audio_router)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            {"error": "Invalid request."},
            status_code=400,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        detail = error.detail
        if isinstance(detail, dict) and "error" in detail:
            payload = detail
        else:
            payload = {"error": str(detail)}
        return JSONResponse(payload, status_code=error.status_code, headers=error.headers)

    @app.exception_handler(FFmpegNotAvailableError)
    async def handle_ffmpeg_error(
        _request: Request,
        _error: FFmpegNotAvailableError,
    ) -> JSONResponse:
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request,
        error: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled server error: %s", error)
        return JSONResponse(
            {"error": "Media conversion failed."},
            status_code=500,
        )

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        logger.warning(
            "FFmpeg and/or ffprobe is not available in PATH. "
            "Media conversion endpoints will return an informative error."
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False)
