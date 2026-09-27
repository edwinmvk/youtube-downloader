from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yt_dlp

logger = logging.getLogger(__name__)


class MediaDownloadError(RuntimeError):
    """Raised when a media download completes without a usable output file."""


class DownloadCancelled(RuntimeError):
    """Raised internally when a user cancellation request is observed."""


ALLOWED_RESOLUTIONS = {"highest", "medium", "lowest"}
MEDIUM_TARGET_HEIGHT = 720


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise MediaDownloadError("Invalid or unsupported URL.")


def validate_resolution(resolution: str | None) -> str:
    value = (resolution or "highest").lower().strip()
    if value not in ALLOWED_RESOLUTIONS:
        raise MediaDownloadError("Unsupported resolution. Use highest, medium or lowest.")
    return value


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


def _format_selector(media_format: str, resolution: str | None) -> str:
    if media_format == "mp3":
        return "bestaudio/best"

    selected_resolution = validate_resolution(resolution)
    if selected_resolution == "highest":
        return "bestvideo+bestaudio/best"
    if selected_resolution == "lowest":
        return "worstvideo+worstaudio/worst"

    # Medium targets 720p. If 720p (or lower) is not available, prefer the next
    # practical tier up to 1080p; if that is unavailable, fall back to the best
    # available stream. This keeps the request working for unusual source formats.
    return (
        "bestvideo[height<=720]+bestaudio/"
        "bestvideo[height>720][height<=1080]+bestaudio/"
        "bestvideo[height>1080][height<=1440]+bestaudio/"
        "bestvideo[height>1440][height<=2160]+bestaudio/"
        "bestvideo+bestaudio/best"
    )


def _selection_note(requested_resolution: str | None, effective_height: int | None) -> str | None:
    if requested_resolution != "medium" or effective_height is None:
        return None
    if effective_height == MEDIUM_TARGET_HEIGHT:
        return None
    return (
        f"720p is not available; using the closest available resolution: "
        f"{effective_height}p."
    )


def _set_progress(
    on_progress: Callable[..., None] | None,
    *,
    status: str,
    downloaded_bytes: int = 0,
    total_bytes: int | None = None,
    speed_bytes_per_second: float | None = None,
    eta_seconds: int | None = None,
    progress: float = 0.0,
    title: str | None = None,
    effective_resolution: int | None = None,
) -> None:
    if on_progress is not None:
        on_progress(
            status=status,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            speed_bytes_per_second=speed_bytes_per_second,
            eta_seconds=eta_seconds,
            progress=progress,
            title=title,
            effective_resolution=effective_resolution,
        )


def download_media(
    url: str,
    media_format: str,
    temp_dir: Path,
    *,
    resolution: str | None = None,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[..., None] | None = None,
) -> tuple[Path, str, int | None, str | None, str | None]:
    """Download media and return (path, filename, effective_height, title, selection_note)."""
    _validate_url(url)

    if media_format not in {"mp3", "mp4"}:
        raise MediaDownloadError("Unsupported format. Use mp3 or mp4.")

    if media_format == "mp4":
        requested_resolution = validate_resolution(resolution)
    else:
        requested_resolution = None

    output_template = str(temp_dir / "%(title)s.%(ext)s")
    pot_provider_url = os.getenv("POT_PROVIDER_URL", "http://127.0.0.1:4416").strip()
    ydl_opts: dict[str, Any] = {
        "format": _format_selector(media_format, requested_resolution),
        "noplaylist": True,
        "outtmpl": output_template,
        "windowsfilenames": True,
        "progress_hooks": [],
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb"],
            },
            "youtubepot-bgutilhttp": {
                "base_url": [pot_provider_url],
            },
        },
    }

    if media_format == "mp3":
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        ydl_opts["merge_output_format"] = "mp4"

    def check_cancel() -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelled()

    def progress_hook(info: dict[str, Any]) -> None:
        check_cancel()

        status = info.get("status")
        title = info.get("title")
        height = info.get("height")

        if status == "downloading":
            downloaded = int(info.get("downloaded_bytes") or 0)
            total = info.get("total_bytes") or info.get("total_bytes_estimate")
            total_int = int(total) if total else None
            percent = (downloaded / total_int * 100.0) if total_int else 0.0
            speed = info.get("speed")
            eta = info.get("eta")
            _set_progress(
                on_progress,
                status="downloading",
                downloaded_bytes=downloaded,
                total_bytes=total_int,
                speed_bytes_per_second=float(speed) if speed is not None else None,
                eta_seconds=int(eta) if eta is not None else None,
                progress=percent,
                title=title,
                effective_resolution=int(height) if height else None,
            )
        elif status == "finished":
            _set_progress(
                on_progress,
                status="processing",
                downloaded_bytes=int(info.get("downloaded_bytes") or 0),
                total_bytes=(
                    int(info["total_bytes"])
                    if info.get("total_bytes")
                    else None
                ),
                speed_bytes_per_second=None,
                eta_seconds=None,
                progress=100.0,
                title=title,
                effective_resolution=int(height) if height else None,
            )

    def postprocessor_hook(info: dict[str, Any]) -> None:
        check_cancel()
        status = info.get("status")
        if status in {"started", "processing"}:
            _set_progress(
                on_progress,
                status="processing",
                progress=100.0,
            )

    ydl_opts["progress_hooks"] = [progress_hook]
    ydl_opts["postprocessor_hooks"] = [postprocessor_hook]

    title_holder: dict[str, Any] = {"title": None, "height": None}
    stream_progress: dict[str, dict[str, Any]] = {}

    def _aggregate_progress() -> tuple[float, int, int | None, float | None, int | None]:
        downloaded_total = sum(int(item.get("downloaded") or 0) for item in stream_progress.values())
        totals = [int(item["total"]) for item in stream_progress.values() if item.get("total")]
        total_total = sum(totals) if totals else None
        speeds = [float(item["speed"]) for item in stream_progress.values() if item.get("speed") is not None]
        aggregate_speed = sum(speeds) if speeds else None

        if total_total:
            percent = min(100.0, downloaded_total / total_total * 100.0)
            if aggregate_speed and aggregate_speed > 0:
                eta = max(0, int((total_total - downloaded_total) / aggregate_speed))
            else:
                eta = None
        else:
            percent_values = [
                float(item["percent"])
                for item in stream_progress.values()
                if item.get("percent") is not None
            ]
            percent = max(percent_values) if percent_values else 0.0
            eta_values = [
                int(item["eta"])
                for item in stream_progress.values()
                if item.get("eta") is not None
            ]
            eta = max(eta_values) if eta_values else None

        return percent, downloaded_total, total_total, aggregate_speed, eta

    def progress_hook(info: dict[str, Any]) -> None:
        check_cancel()

        status = info.get("status")
        title = info.get("title")
        height = info.get("height")
        if title:
            title_holder["title"] = title
        if height:
            title_holder["height"] = int(height)

        stream_key = str(
            info.get("filename")
            or info.get("tmpfilename")
            or info.get("format_id")
            or "default"
        )
        stream = stream_progress.setdefault(
            stream_key,
            {"downloaded": 0, "total": None, "speed": None, "eta": None, "percent": 0.0},
        )

        if status == "downloading":
            downloaded = int(info.get("downloaded_bytes") or 0)
            total = info.get("total_bytes") or info.get("total_bytes_estimate")
            stream["downloaded"] = downloaded
            stream["total"] = int(total) if total else stream.get("total")
            stream["speed"] = float(info["speed"]) if info.get("speed") is not None else None
            stream["eta"] = int(info["eta"]) if info.get("eta") is not None else None
            if stream.get("total"):
                stream["percent"] = downloaded / stream["total"] * 100.0
            else:
                percent_text = str(info.get("_percent_str", "0%"))
                try:
                    stream["percent"] = float(percent_text.strip().rstrip("%").strip())
                except ValueError:
                    stream["percent"] = 0.0

            percent, downloaded_total, total_total, aggregate_speed, eta = _aggregate_progress()
            _set_progress(
                on_progress,
                status="downloading",
                downloaded_bytes=downloaded_total,
                total_bytes=total_total,
                speed_bytes_per_second=aggregate_speed,
                eta_seconds=eta,
                progress=percent,
                title=title_holder["title"],
                effective_resolution=title_holder["height"],
            )

        elif status == "finished":
            if info.get("total_bytes"):
                stream["total"] = int(info["total_bytes"])
            stream["downloaded"] = int(
                info.get("downloaded_bytes")
                or stream.get("total")
                or stream.get("downloaded")
                or 0
            )
            if stream.get("total"):
                stream["downloaded"] = int(stream["total"])
            stream["speed"] = None
            stream["eta"] = None
            stream["percent"] = 100.0

            percent, downloaded_total, total_total, aggregate_speed, eta = _aggregate_progress()
            _set_progress(
                on_progress,
                status="processing",
                downloaded_bytes=downloaded_total,
                total_bytes=total_total,
                speed_bytes_per_second=aggregate_speed,
                eta_seconds=eta,
                progress=percent,
                title=title_holder["title"],
                effective_resolution=title_holder["height"],
            )

    def postprocessor_hook(info: dict[str, Any]) -> None:
        check_cancel()
        status = info.get("status")
        if status in {"started", "processing"}:
            _set_progress(
                on_progress,
                status="processing",
                progress=100.0,
                title=title_holder["title"],
                effective_resolution=title_holder["height"],
            )

    ydl_opts["progress_hooks"] = [progress_hook]
    ydl_opts["postprocessor_hooks"] = [postprocessor_hook]

    try:
        check_cancel()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        check_cancel()
    except DownloadCancelled:
        raise

    output_path = _find_output(temp_dir, media_format)
    filename = output_path.name
    title = title_holder["title"] or output_path.stem
    effective_height = title_holder["height"]
    note = _selection_note(requested_resolution, effective_height)

    return output_path, filename, effective_height, title, note
