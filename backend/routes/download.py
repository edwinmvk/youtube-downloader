from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yt_dlp
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from services.ffmpeg_service import FFmpegNotAvailableError, ensure_ffmpeg_available
from services.job_service import DownloadJob, job_manager
from services.yt_dlp_service import (
    DownloadCancelled,
    MediaDownloadError,
    download_media,
    validate_resolution,
)

logger = logging.getLogger(__name__)

download_router = APIRouter()


def _validate_request_body(
    data: Any,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not isinstance(data, dict) or "url" not in data or "format" not in data:
        return None, None, None, "Invalid request. URL and format are required."

    url = data.get("url")
    media_format = data.get("format")
    if not isinstance(url, str) or not url.strip():
        return None, None, None, "Invalid request. URL and format are required."

    if media_format not in {"mp3", "mp4"}:
        return None, None, None, "Unsupported format. Use mp3 or mp4."

    resolution = None
    if media_format == "mp4":
        resolution = data.get("resolution", "highest")
        if not isinstance(resolution, str):
            return None, None, None, (
                "Unsupported resolution. Use highest, medium or lowest."
            )
        try:
            resolution = validate_resolution(resolution)
        except MediaDownloadError as error:
            return None, None, None, str(error)

    return url.strip(), media_format, resolution, None


async def _read_json_body(request: Request) -> Any:
    try:
        return await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


def _update_job_from_progress(job: DownloadJob, **data: Any) -> None:
    job_manager.update(
        job.job_id,
        status="downloading" if data.get("status") == "downloading" else "processing",
        phase="downloading" if data.get("status") == "downloading" else "processing",
        progress=max(job.progress, float(data.get("progress") or 0.0)),
        downloaded_bytes=int(data.get("downloaded_bytes") or 0),
        total_bytes=data.get("total_bytes"),
        speed_bytes_per_second=data.get("speed_bytes_per_second"),
        eta_seconds=data.get("eta_seconds"),
        title=data.get("title") or job.title,
        effective_resolution=data.get("effective_resolution") or job.effective_resolution,
    )


def _run_async_job(job: DownloadJob) -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"media_job_{job.job_id}_"))
    job_manager.update(job.job_id, temp_dir=temp_dir)

    try:
        ensure_ffmpeg_available()
        if job.cancel_event.is_set():
            job_manager.mark_cancelled(job)
            return

        output_path, filename, effective_height, title, selection_note = download_media(
            url=job.url,
            media_format=job.media_format,
            temp_dir=temp_dir,
            resolution=job.requested_resolution,
            cancel_event=job.cancel_event,
            on_progress=lambda **data: _update_job_from_progress(job, **data),
        )

        if job.cancel_event.is_set():
            job_manager.mark_cancelled(job)
            return

        job_manager.update(
            job.job_id,
            title=title,
            effective_resolution=effective_height,
            selection_note=selection_note,
        )
        job_manager.mark_completed(job, output_path, filename)

    except DownloadCancelled:
        logger.info("Download job %s was cancelled.", job.job_id)
        job_manager.mark_cancelled(job)
    except yt_dlp.utils.DownloadError as error:
        logger.warning("yt-dlp failed for job %s: %s", job.job_id, error)
        job_manager.mark_failed(job, "Unable to download the requested media.")
    except MediaDownloadError as error:
        logger.warning("Media download failed for job %s: %s", job.job_id, error)
        job_manager.mark_failed(job, str(error))
    except FFmpegNotAvailableError:
        job_manager.mark_failed(
            job,
            "FFmpeg is not installed or is not available in PATH.",
        )
    except Exception:
        logger.exception("Unexpected error while running download job %s", job.job_id)
        job_manager.mark_failed(job, "Unable to download the requested media.")


@download_router.post("/api/download")
async def download_from_url(request: Request):
    """Backward-compatible synchronous endpoint."""
    data = await _read_json_body(request)
    url, media_format, resolution, validation_error = _validate_request_body(data)
    if validation_error:
        return JSONResponse({"error": validation_error}, status_code=400)

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )

    assert url is not None
    assert media_format is not None
    temp_dir = Path(tempfile.mkdtemp(prefix="media_downloader_"))

    try:
        output_path, download_name, _, _, _ = await run_in_threadpool(
            download_media,
            url,
            media_format,
            temp_dir,
            resolution=resolution,
        )

        mimetype = "audio/mpeg" if media_format == "mp3" else "video/mp4"
        headers = {}
        if download_name.isascii():
            headers["X-Download-Filename"] = download_name

        return FileResponse(
            output_path,
            media_type=mimetype,
            filename=download_name,
            headers=headers,
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )

    except yt_dlp.utils.DownloadError as error:
        logger.warning("yt-dlp download error for %s: %s", url, error)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(
            {"error": "Unable to download the requested media."},
            status_code=400,
        )
    except MediaDownloadError as error:
        logger.warning("Media download failed for %s: %s", url, error)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": str(error)}, status_code=400)
    except FFmpegNotAvailableError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )
    except Exception:
        logger.exception("Unexpected error while downloading media from %s", url)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(
            {"error": "Unable to download the requested media."},
            status_code=500,
        )


@download_router.post("/api/download/start")
async def start_download(request: Request):
    data = await _read_json_body(request)
    url, media_format, resolution, validation_error = _validate_request_body(data)
    if validation_error:
        return JSONResponse({"error": validation_error}, status_code=400)

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )

    assert url is not None
    assert media_format is not None
    job = job_manager.create(url, media_format, resolution)
    try:
        job_manager.submit(job, _run_async_job)
    except Exception:
        logger.exception("Failed to queue download job %s", job.job_id)
        job_manager.mark_failed(job, "Unable to download the requested media.")
        return JSONResponse(
            {"error": "Unable to download the requested media."},
            status_code=500,
        )

    return JSONResponse(
        {
            "job_id": job.job_id,
            "status": "queued",
            "progress_url": f"/api/download/progress/{job.job_id}",
            "cancel_url": f"/api/download/cancel/{job.job_id}",
            "file_url": f"/api/download/file/{job.job_id}",
        },
        status_code=202,
    )


@download_router.get("/api/download/progress/{job_id}")
def download_progress(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        return JSONResponse(
            {"error": "Download job not found or expired."},
            status_code=404,
        )
    return job.snapshot()


@download_router.post("/api/download/cancel/{job_id}")
def cancel_download(job_id: str):
    job, state = job_manager.request_cancel(job_id)
    if job is None:
        return JSONResponse(
            {"error": "Download job not found or expired."},
            status_code=404,
        )

    if state == "terminal":
        return {
            "job_id": job.job_id,
            "status": job.status,
            "message": "Download has already reached a terminal state.",
        }

    if state == "cancelled":
        return {
            "job_id": job.job_id,
            "status": "cancelled",
            "message": "Download cancelled.",
        }

    return JSONResponse(
        {
            "job_id": job.job_id,
            "status": "cancelling",
            "message": "Download cancellation requested.",
        },
        status_code=202,
    )


@download_router.get("/api/download/file/{job_id}")
def download_completed_file(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        return JSONResponse(
            {"error": "Download job not found or expired."},
            status_code=404,
        )

    if job.status != "completed" or job.output_path is None or not job.output_path.exists():
        if job.status in {"failed", "cancelled"}:
            return JSONResponse(
                {"error": job.error or f"Download is {job.status}."},
                status_code=409,
            )
        return JSONResponse(
            {"error": "Download is not completed yet."},
            status_code=409,
        )

    mimetype = "audio/mpeg" if job.media_format == "mp3" else "video/mp4"
    download_name = job.filename or job.output_path.name
    headers = {}
    if download_name.isascii():
        headers["X-Download-Filename"] = download_name

    return FileResponse(
        job.output_path,
        media_type=mimetype,
        filename=download_name,
        headers=headers,
        background=BackgroundTask(job_manager.finish_file_delivery, job_id),
    )
