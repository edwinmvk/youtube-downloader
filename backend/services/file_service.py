import re

from werkzeug.utils import secure_filename

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
MAX_FILENAME_LENGTH = 180

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Return a filesystem-safe, human-readable filename component."""
    value = (filename or "").strip()
    value = value.replace("/", "_").replace("\\", "_")
    value = _INVALID_FILENAME_CHARS.sub("_", value)
    value = value.rstrip(" .")

    # secure_filename prevents path traversal and handles platform-specific names.
    safe = secure_filename(value)
    if not safe:
        return "media"

    return safe[:max_length].rstrip(" .") or "media"
