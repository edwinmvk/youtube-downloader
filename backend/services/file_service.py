import re
import unicodedata

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
MAX_FILENAME_LENGTH = 180

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Return a filesystem-safe filename while preserving Unicode characters.

    Unlike Werkzeug's ``secure_filename``, this helper intentionally does not
    transliterate non-ASCII text. Malayalam, Hindi, English, mixed-language,
    accented and other Unicode titles should remain readable in the generated
    filename whenever the underlying filesystem supports them.
    """
    value = unicodedata.normalize("NFC", filename or "").strip()

    # Remove path separators, control characters and Windows-invalid filename
    # characters without stripping otherwise valid Unicode letters/scripts.
    value = _INVALID_FILENAME_CHARS.sub("_", value)
    value = value.replace("/", "_").replace("\\", "_")
    value = value.rstrip(" .")

    if not value:
        return "media"

    # Windows treats these device names as reserved even with no extension.
    stem = value.split(".", 1)[0].upper()
    if stem in _RESERVED_WINDOWS_NAMES:
        value = f"_{value}"

    # Avoid hidden/path-like names such as '.' and '..'.
    if value in {".", ".."}:
        value = "media"

    value = value[:max_length].rstrip(" .")
    return value or "media"


def unique_filename(filename: str, used_names: set[str]) -> str:
    """Return a collision-free filename while preserving the original name."""
    if filename not in used_names:
        used_names.add(filename)
        return filename

    stem, dot, suffix = filename.rpartition(".")
    if not dot:
        stem, suffix = filename, ""

    counter = 2
    while True:
        candidate = f"{stem} ({counter})"
        if suffix:
            candidate = f"{candidate}.{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1
