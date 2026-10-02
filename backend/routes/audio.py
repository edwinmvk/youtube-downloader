from __future__ import annotations

import logging
import math
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from services.audio_service import (
    ALLOWED_AUDIO_EXTENSIONS,
    AudioProcessingError,
    merge_audio_files,
    trim_audio,
)
from services.ffmpeg_service import FFmpegNotAvailableError, ensure_ffmpeg_available
from services.file_service import sanitize_filename, unique_filename

logger = logging.getLogger(__name__)

audio_router = APIRouter()
MAX_MERGE_FILES = 10


def _validate_audio_file(uploaded_file: UploadFile) -> str | None:
    if not uploaded_file.filename:
        return "One or more audio files have no filename."
    extension = Path(uploaded_file.filename).suffix.lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        return (
            f"Unsupported audio format: {uploaded_file.filename}. "
            "Use MP3, WAV, M4A, AAC, FLAC, OGG, OPUS or WEBM."
        )
    return None


def _save_upload(uploaded_file: UploadFile, destination: Path) -> None:
    uploaded_file.file.seek(0)
    with destination.open("wb") as output:
        shutil.copyfileobj(uploaded_file.file, output)
    if not destination.exists() or destination.stat().st_size == 0:
        raise AudioProcessingError(f"Uploaded file is empty: {uploaded_file.filename or 'audio file'}")


@audio_router.post("/api/audio/trim")
def trim_audio_endpoint(
    file: UploadFile = File(...),
    start_seconds: float = Form(...),
    end_seconds: float = Form(...),
):
    validation_error = _validate_audio_file(file)
    if validation_error:
        return JSONResponse({"error": validation_error}, status_code=400)

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )

    if not math.isfinite(start_seconds) or not math.isfinite(end_seconds):
        return JSONResponse({"error": "The trim range is invalid."}, status_code=400)
    if start_seconds < 0 or end_seconds <= start_seconds:
        return JSONResponse({"error": "The trim range is invalid."}, status_code=400)

    temp_dir = Path(tempfile.mkdtemp(prefix="audio_trim_"))

    try:
        original_name = Path(file.filename or "audio.mp3").name
        stem = sanitize_filename(Path(original_name).stem) or "trimmed_audio"
        input_path = temp_dir / f"input{Path(original_name).suffix.lower()}"
        output_name = f"{stem} - trimmed.mp3"
        output_path = temp_dir / output_name

        _save_upload(file, input_path)
        trim_audio(input_path, output_path, start_seconds, end_seconds)

        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename=output_name,
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )
    except (FFmpegNotAvailableError, AudioProcessingError) as error:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": str(error)}, status_code=400)
    except Exception:
        logger.exception("Unexpected error trimming audio")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": "Audio trimming failed."}, status_code=500)


@audio_router.post("/api/audio/merge")
def merge_audio_endpoint(
    files: list[UploadFile] = File(...),
):
    if not files:
        return JSONResponse({"error": "Select at least two audio files."}, status_code=400)
    if len(files) > MAX_MERGE_FILES:
        return JSONResponse(
            {"error": f"You can merge a maximum of {MAX_MERGE_FILES} audio files at once."},
            status_code=400,
        )
    if len(files) < 2:
        return JSONResponse({"error": "Select at least two audio files."}, status_code=400)

    for uploaded_file in files:
        validation_error = _validate_audio_file(uploaded_file)
        if validation_error:
            return JSONResponse({"error": validation_error}, status_code=400)

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="audio_merge_"))

    try:
        input_paths: list[Path] = []
        for index, uploaded_file in enumerate(files, start=1):
            extension = Path(uploaded_file.filename or ".mp3").suffix.lower()
            input_path = temp_dir / f"input_{index}{extension}"
            _save_upload(uploaded_file, input_path)
            input_paths.append(input_path)

        first_stem = sanitize_filename(Path(files[0].filename or "audio").stem) or "audio"
        output_name = f"{first_stem} - merged.mp3"
        output_path = temp_dir / output_name

        merge_audio_files(input_paths, output_path, temp_dir)

        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename=output_name,
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )
    except (FFmpegNotAvailableError, AudioProcessingError) as error:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": str(error)}, status_code=400)
    except Exception:
        logger.exception("Unexpected error merging audio")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": "Audio merging failed."}, status_code=500)
