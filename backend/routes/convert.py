from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from services.ffmpeg_service import (
    FFmpegNotAvailableError,
    convert_video_to_mp3,
    ensure_ffmpeg_available,
)
from services.file_service import (
    ALLOWED_VIDEO_EXTENSIONS,
    sanitize_filename,
    unique_filename,
)

logger = logging.getLogger(__name__)

convert_router = APIRouter()
MAX_CONVERT_FILES = 10


def _validate_uploaded_files(files: list[UploadFile]) -> str | None:
    if not files:
        return "No file was uploaded."

    if len(files) > MAX_CONVERT_FILES:
        return f"You can convert a maximum of {MAX_CONVERT_FILES} files at once."

    for uploaded_file in files:
        if not uploaded_file.filename:
            return "One or more uploaded files have no filename."

        extension = Path(uploaded_file.filename).suffix.lower()
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            return f"Unsupported video format: {uploaded_file.filename}"

    return None


def _create_conversion_zip(output_files: list[Path], zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        used_names: set[str] = set()
        for output_file in output_files:
            archive_name = unique_filename(output_file.name, used_names)
            archive.write(output_file, arcname=archive_name)


@convert_router.post("/api/convert")
def convert_video(
    files: list[UploadFile] | None = File(default=None),
    file: UploadFile | None = File(default=None),
):
    uploaded_files = list(files or [])
    if not uploaded_files and file is not None:
        uploaded_files = [file]

    validation_error = _validate_uploaded_files(uploaded_files)
    if validation_error:
        return JSONResponse({"error": validation_error}, status_code=400)

    try:
        ensure_ffmpeg_available()
    except FFmpegNotAvailableError:
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="media_convert_"))

    try:
        output_files: list[Path] = []
        used_output_names: set[str] = set()

        for index, uploaded_file in enumerate(uploaded_files, start=1):
            original_filename = Path(uploaded_file.filename or f"video_{index}.mp4").name
            original_stem = Path(original_filename).stem
            safe_stem = sanitize_filename(original_stem) or f"converted_audio_{index}"
            extension = Path(original_filename).suffix.lower()

            input_path = temp_dir / f"input_{index}{extension}"
            output_filename = unique_filename(
                f"{safe_stem}.mp3",
                used_output_names,
            )
            output_path = temp_dir / output_filename

            uploaded_file.file.seek(0)
            with input_path.open("wb") as destination:
                shutil.copyfileobj(uploaded_file.file, destination)

            if not input_path.exists() or input_path.stat().st_size == 0:
                raise ValueError(f"Uploaded file is empty: {original_filename}")

            convert_video_to_mp3(input_path, output_path)
            output_files.append(output_path)

        if len(output_files) == 1:
            output_path = output_files[0]
            return FileResponse(
                output_path,
                media_type="audio/mpeg",
                filename=output_path.name,
                background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
            )

        zip_path = temp_dir / "converted_audio.zip"
        _create_conversion_zip(output_files, zip_path)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=zip_path.name,
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )

    except FFmpegNotAvailableError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(
            {"error": "FFmpeg is not installed or is not available in PATH."},
            status_code=500,
        )
    except ValueError as error:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": str(error)}, status_code=400)
    except Exception:
        logger.exception("Unexpected error converting uploaded video files")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse({"error": "Media conversion failed."}, status_code=500)
