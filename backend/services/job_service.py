from __future__ import annotations

import logging
import os
import shutil
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"completed", "cancelled", "failed"}


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        logger.warning("Invalid %s=%r; falling back to %s.", name, raw, default)
        return default


@dataclass
class DownloadJob:
    job_id: str
    url: str
    media_format: str
    requested_resolution: str | None
    status: str = "queued"
    phase: str = "queued"
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed_bytes_per_second: float | None = None
    eta_seconds: int | None = None
    title: str | None = None
    filename: str | None = None
    effective_resolution: int | None = None
    selection_note: str | None = None
    error: str | None = None
    cancel_requested: bool = False
    temp_dir: Path | None = None
    output_path: Path | None = None
    created_at: float = field(default_factory=time)
    completed_at: float | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    future: Future[Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": round(max(0.0, min(100.0, self.progress)), 1),
            "phase": self.phase,
            "format": self.media_format,
            "requested_resolution": self.requested_resolution,
            "effective_resolution": self.effective_resolution,
            "selection_note": self.selection_note,
            "title": self.title,
            "filename": self.filename,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "speed_bytes_per_second": self.speed_bytes_per_second,
            "eta_seconds": self.eta_seconds,
            "error": self.error,
            "cancel_requested": self.cancel_requested,
        }


class DownloadJobManager:
    """In-memory job registry and worker pool for the async download API."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, DownloadJob] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=_positive_int_env("MAX_CONCURRENT_DOWNLOADS", 2),
            thread_name_prefix="media-download",
        )
        self._job_ttl_seconds = _positive_int_env("DOWNLOAD_JOB_TTL_SECONDS", 1800)

    def create(self, url: str, media_format: str, resolution: str | None) -> DownloadJob:
        job = DownloadJob(
            job_id=uuid.uuid4().hex,
            url=url,
            media_format=media_format,
            requested_resolution=resolution,
        )
        with self._lock:
            self._cleanup_expired_locked()
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            self._cleanup_expired_locked()
            return self._jobs.get(job_id)

    def submit(self, job: DownloadJob, target: Callable[[DownloadJob], None]) -> None:
        future = self._executor.submit(target, job)
        with self._lock:
            job.future = future

    def request_cancel(self, job_id: str) -> tuple[DownloadJob | None, str]:
        with self._lock:
            self._cleanup_expired_locked()
            job = self._jobs.get(job_id)
            if job is None:
                return None, "not_found"

            if job.status in TERMINAL_STATUSES:
                return job, "terminal"

            job.cancel_requested = True
            job.cancel_event.set()

            if job.status == "queued":
                job.status = "cancelled"
                job.phase = "cancelled"
                job.progress = 0.0
                job.completed_at = time()
                self._cleanup_job_resources_locked(job)
                return job, "cancelled"

            return job, "cancelling"

    def update(self, job_id: str, **changes: Any) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for key, value in changes.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            return job

    def mark_completed(self, job: DownloadJob, output_path: Path, filename: str) -> None:
        with self._lock:
            job.output_path = output_path
            job.filename = filename
            job.progress = 100.0
            job.phase = "completed"
            job.status = "completed"
            job.completed_at = time()

        timer = threading.Timer(
            self._job_ttl_seconds,
            self.expire_if_still_pending,
            args=(job.job_id,),
        )
        timer.daemon = True
        timer.start()

    def mark_cancelled(self, job: DownloadJob) -> None:
        with self._lock:
            job.status = "cancelled"
            job.phase = "cancelled"
            job.error = None
            job.completed_at = time()
            self._cleanup_job_resources_locked(job)

    def mark_failed(self, job: DownloadJob, error_message: str) -> None:
        with self._lock:
            job.status = "failed"
            job.phase = "failed"
            job.error = error_message
            job.completed_at = time()
            self._cleanup_job_resources_locked(job)

    def finish_file_delivery(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.pop(job_id, None)
            if job is not None:
                self._cleanup_job_resources_locked(job)

    def expire_if_still_pending(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.status == "completed" and job.completed_at is not None:
                self._jobs.pop(job_id, None)
                self._cleanup_job_resources_locked(job)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _cleanup_expired_locked(self) -> None:
        now = time()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.completed_at is not None
            and now - job.completed_at >= self._job_ttl_seconds
        ]
        for job_id in expired:
            job = self._jobs.pop(job_id, None)
            if job is not None:
                self._cleanup_job_resources_locked(job)

    @staticmethod
    def _cleanup_job_resources_locked(job: DownloadJob) -> None:
        if job.temp_dir is not None:
            shutil.rmtree(job.temp_dir, ignore_errors=True)
            job.temp_dir = None
            job.output_path = None


job_manager = DownloadJobManager()
