from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from services.ffmpeg_service import FFmpegNotAvailableError, ensure_ffmpeg_available


class AudioProcessingError(RuntimeError):
    """Raised when an audio trim or merge operation cannot be completed."""


ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".webm",
}


def _run_ffmpeg(command: list[str], output_path: Path) -> None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise FFmpegNotAvailableError(
            "FFmpeg is not installed or is not available in PATH."
        ) from error

    if completed.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        stderr = completed.stderr.strip()
        raise AudioProcessingError(stderr or "FFmpeg failed to process the audio.")


def get_audio_duration(input_path: Path) -> float:
    ensure_ffmpeg_available()
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(input_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise FFmpegNotAvailableError(
            "FFmpeg is not installed or is not available in PATH."
        ) from error

    if completed.returncode != 0:
        raise AudioProcessingError(completed.stderr.strip() or "Unable to inspect the audio file.")

    try:
        duration = float(json.loads(completed.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise AudioProcessingError("Unable to determine the audio duration.") from error

    if duration <= 0:
        raise AudioProcessingError("The selected audio file has no usable duration.")

    return duration


def trim_audio(
    input_path: Path,
    output_path: Path,
    start_seconds: float,
    end_seconds: float,
) -> None:
    duration = get_audio_duration(input_path)

    if start_seconds < 0 or end_seconds <= start_seconds:
        raise AudioProcessingError("The trim range is invalid.")
    if end_seconds > duration + 0.05:
        raise AudioProcessingError(
            f"The trim end must be within the audio duration ({duration:.2f} seconds)."
        )

    clip_duration = end_seconds - start_seconds

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-ss",
        f"{start_seconds:.3f}",
        "-t",
        f"{clip_duration:.3f}",
        "-map",
        "0:a:0",
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "-id3v2_version",
        "3",
        str(output_path),
    ]
    _run_ffmpeg(command, output_path)


def merge_audio_files(
    input_paths: list[Path],
    output_path: Path,
    work_dir: Path,
) -> None:
    if len(input_paths) < 2:
        raise AudioProcessingError("Select at least two audio files to merge.")

    normalized_paths: list[Path] = []

    # Normalize every source to the same MP3 parameters first. This makes the
    # subsequent concat operation reliable even when the uploaded files use
    # different codecs, sample rates, or containers.
    for index, input_path in enumerate(input_paths, start=1):
        normalized_path = work_dir / f"normalized_{index}.mp3"
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-map",
            "0:a:0",
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-b:a",
            "192k",
            "-id3v2_version",
            "3",
            str(normalized_path),
        ]
        _run_ffmpeg(command, normalized_path)
        normalized_paths.append(normalized_path)

    concat_file = work_dir / "concat.txt"
    with concat_file.open("w", encoding="utf-8", newline="\n") as handle:
        for path in normalized_paths:
            # FFmpeg concat demuxer accepts single-quoted paths. Escape quotes
            # and backslashes so uploaded Unicode filenames remain safe.
            escaped = str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        "-id3v2_version",
        "3",
        str(output_path),
    ]
    _run_ffmpeg(command, output_path)
