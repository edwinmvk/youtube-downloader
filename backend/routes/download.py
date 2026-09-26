import logging
import shutil
import tempfile
from pathlib import Path

import yt_dlp
from flask import Blueprint, jsonify, request, send_file

from services.ffmpeg_service import FFmpegNotAvailableError, ensure_ffmpeg_available
from services.yt_dlp_service import MediaDownloadError, download_media

logger = logging.getLogger(__name__)

download_bp = Blueprint("download", __name__)


@download_bp.post("/api/download")
def download_from_url():
    data = request.get_json(silent=True)

    if not data or "url" not in data or "format" not in data:
        return jsonify(error="Invalid request. URL and format are required."), 400

    url = data.get("url")
    media_format = data.get("format")

    if not isinstance(url, str) or not url.strip():
        return jsonify(error="Invalid request. URL and format are required."), 400

    if media_format not in {"mp3", "mp4"}:
        return jsonify(error="Unsupported format. Use mp3 or mp4."), 400

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500

    temp_dir = Path(tempfile.mkdtemp(prefix="media_downloader_"))

    try:
        output_path, download_name = download_media(
            url=url.strip(),
            media_format=media_format,
            temp_dir=temp_dir,
        )

        mimetype = "audio/mpeg" if media_format == "mp3" else "video/mp4"
        response = send_file(
            output_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name,
            conditional=True,
        )
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
