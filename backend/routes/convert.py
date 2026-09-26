import logging
import shutil
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services.ffmpeg_service import FFmpegNotAvailableError, convert_video_to_mp3, ensure_ffmpeg_available
from services.file_service import ALLOWED_VIDEO_EXTENSIONS, sanitize_filename

logger = logging.getLogger(__name__)

convert_bp = Blueprint("convert", __name__)


@convert_bp.post("/api/convert")
def convert_video():
    uploaded_file: FileStorage | None = request.files.get("file")

    if uploaded_file is None:
        return jsonify(error="No file was uploaded."), 400

    if not uploaded_file.filename:
        return jsonify(error="No file was uploaded."), 400

    extension = Path(uploaded_file.filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify(error="Unsupported video format."), 400

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500

    temp_dir = Path(tempfile.mkdtemp(prefix="media_convert_"))

    try:
        original_stem = Path(uploaded_file.filename).stem
        safe_stem = sanitize_filename(original_stem) or "converted_audio"
        input_path = temp_dir / f"input{extension}"
        output_path = temp_dir / f"{safe_stem}.mp3"

        uploaded_file.save(input_path)

        max_bytes = request.max_content_length
        if max_bytes is not None and input_path.stat().st_size > max_bytes:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify(error="File is too large."), 413

        convert_video_to_mp3(input_path, output_path)

        response = send_file(
            output_path,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=output_path.name,
            conditional=True,
        )
        response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return response

    except FFmpegNotAvailableError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500
    except Exception:
        logger.exception("Unexpected error converting uploaded video")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error="Media conversion failed."), 500
