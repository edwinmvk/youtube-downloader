import shutil
import subprocess
from pathlib import Path


class FFmpegNotAvailableError(RuntimeError):
    """Raised when ffmpeg/ffprobe cannot be found in PATH."""


def ensure_ffmpeg_available() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise FFmpegNotAvailableError(
            "FFmpeg is not installed or is not available in PATH."
        )


def convert_video_to_mp3(input_path: Path, output_path: Path) -> None:
    """Extract the first available audio stream from a video into MP3."""
    ensure_ffmpeg_available()

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-map",
        "0:a:0",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output_path),
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

    if completed.returncode != 0 or not output_path.exists():
        stderr = completed.stderr.strip()
        raise RuntimeError(stderr or "FFmpeg failed to convert the video.")
