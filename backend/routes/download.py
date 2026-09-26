from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

import yt_dlp
from flask import Blueprint, jsonify, request, send_file

from services.ffmpeg_service import FFmpegNotAvailableError, ensure_ffmpeg_available
from services.job_service import DownloadJob, job_manager
from services.yt_dlp_service import (
    DownloadCancelled,
    MediaDownloadError,
    validate_resolution,
    download_media,
)

logger = logging.getLogger(__name__)

download_bp = Blueprint("download", __name__)


def _validate_request_body(
    data: dict | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not data or "url" not in data or "format" not in data:
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


def _update_job_from_progress(job: DownloadJob, **data) -> None:
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


@download_bp.post("/api/download")
def download_from_url():
    """Backward-compatible synchronous endpoint."""
    data = request.get_json(silent=True)
    url, media_format, resolution, validation_error = _validate_request_body(data)
    if validation_error:
        return jsonify(error=validation_error), 400

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500

    temp_dir = Path(tempfile.mkdtemp(prefix="media_downloader_"))

    try:
        output_path, download_name, _, _, _ = download_media(
            url=url,
            media_format=media_format,
            temp_dir=temp_dir,
            resolution=resolution,
        )

        mimetype = "audio/mpeg" if media_format == "mp3" else "video/mp4"
        response = send_file(
            output_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name,
            conditional=True,
        )
        if download_name.isascii():
            response.headers["X-Download-Filename"] = download_name
        response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return response

    except yt_dlp.utils.DownloadError as error:
        logger.warning("yt-dlp download error for %s: %s", url, error)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error="Unable to download the requested media."), 400
    except MediaDownloadError as error:
        logger.warning("Media download failed for %s: %s", url, error)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error=str(error)), 400
    except FFmpegNotAvailableError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500
    except Exception:
        logger.exception("Unexpected error while downloading media from %s", url)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error="Unable to download the requested media."), 500


@download_bp.post("/api/download/start")
def start_download():
    data = request.get_json(silent=True)
    url, media_format, resolution, validation_error = _validate_request_body(data)
    if validation_error:
        return jsonify(error=validation_error), 400

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500

    job = job_manager.create(url, media_format, resolution)
    try:
        job_manager.submit(job, _run_async_job)
    except Exception:
        logger.exception("Failed to queue download job %s", job.job_id)
        job_manager.mark_failed(job, "Unable to download the requested media.")
        return jsonify(error="Unable to download the requested media."), 500

    return jsonify(
        job_id=job.job_id,
        status="queued",
        progress_url=f"/api/download/progress/{job.job_id}",
        cancel_url=f"/api/download/cancel/{job.job_id}",
        file_url=f"/api/download/file/{job.job_id}",
    ), 202


@download_bp.get("/api/download/progress/<job_id>")
def download_progress(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        return jsonify(error="Download job not found or expired."), 404
    return jsonify(job.snapshot())


@download_bp.post("/api/download/cancel/<job_id>")
def cancel_download(job_id: str):
    job, state = job_manager.request_cancel(job_id)
    if job is None:
        return jsonify(error="Download job not found or expired."), 404

    if state == "terminal":
        return jsonify(
            job_id=job.job_id,
            status=job.status,
            message="Download has already reached a terminal state.",
        ), 200

    if state == "cancelled":
        return jsonify(
            job_id=job.job_id,
            status="cancelled",
            message="Download cancelled.",
        ), 200

    return jsonify(
        job_id=job.job_id,
        status="cancelling",
        message="Download cancellation requested.",
    ), 202


@download_bp.get("/api/download/file/<job_id>")
def download_completed_file(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        return jsonify(error="Download job not found or expired."), 404

    if job.status != "completed" or job.output_path is None or not job.output_path.exists():
        if job.status in {"failed", "cancelled"}:
            return jsonify(error=job.error or f"Download is {job.status}."), 409
        return jsonify(error="Download is not completed yet."), 409

    mimetype = "audio/mpeg" if job.media_format == "mp3" else "video/mp4"
    response = send_file(
        job.output_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=job.filename or job.output_path.name,
        conditional=True,
    )
    download_name = job.filename or job.output_path.name
    if download_name.isascii():
        response.headers["X-Download-Filename"] = download_name
    response.call_on_close(lambda: job_manager.finish_file_delivery(job_id))
    return response
