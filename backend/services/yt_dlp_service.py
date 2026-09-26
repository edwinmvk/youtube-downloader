from pathlib import Path
from urllib.parse import urlparse

import yt_dlp


class MediaDownloadError(RuntimeError):
    """Raised when a media download completes without a usable output file."""


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise MediaDownloadError("Invalid or unsupported URL.")


def _find_output(temp_dir: Path, media_format: str) -> Path:
    expected_suffix = f".{media_format}"
    candidates = [
        p
        for p in temp_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() == expected_suffix
        and not p.name.endswith((".part", ".ytdl"))
    ]

    if not candidates:
        raise MediaDownloadError("Unable to download the requested media.")

    return max(candidates, key=lambda p: p.stat().st_mtime)


def download_media(url: str, media_format: str, temp_dir: Path) -> tuple[Path, str]:
    """Download one URL to the temporary directory and return the final file."""
    _validate_url(url)

    if media_format not in {"mp3", "mp4"}:
        raise MediaDownloadError("Unsupported format. Use mp3 or mp4.")

    # Keep the yt-dlp flow close to the known-working CLI command:
    #   -f bestaudio/best --extract-audio --audio-format mp3 --audio-quality 192K
    # For MP3, FFmpegExtractAudio is the explicit conversion step required by the API spec.
    output_template = str(temp_dir / "%(title)s.%(ext)s")

    if media_format == "mp3":
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": output_template,
            "windowsfilenames": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "outtmpl": output_template,
            "windowsfilenames": True,
        }

    # Do not perform a separate extract_info(download=False) call here.
    # The working yt-dlp download flow should perform extraction and download in one operation.
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    output_path = _find_output(temp_dir, media_format)
    return output_path, output_path.name
