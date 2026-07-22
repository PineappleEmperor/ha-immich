"""Data models for the Immich Extras integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aioimmich.server.models import ImmichServerStatistics
    from aioimmich.users.models import ImmichUserObject


@dataclass(frozen=True)
class JobCounts:
    """Job counts for a single Immich job queue."""

    active: int
    waiting: int
    completed: int
    failed: int
    delayed: int
    paused: int


@dataclass(frozen=True)
class ImmichExtrasData:
    """Data returned by one coordinator refresh."""

    my_user: ImmichUserObject
    licensed: bool
    people_count: int
    tags_count: int
    albums_count: int
    statistics: ImmichServerStatistics | None
    jobs: dict[str, JobCounts] | None


def parse_jobs(raw: dict) -> dict[str, JobCounts]:
    """Parse the raw ``GET /api/jobs`` payload into per-queue job counts.

    The payload maps each queue name to ``{"jobCounts": {...}, "queueStatus": {...}}``.
    Missing count fields default to 0 so a partial payload never raises.
    """
    result: dict[str, JobCounts] = {}
    for queue, info in raw.items():
        counts = info.get("jobCounts", {}) if isinstance(info, dict) else {}
        result[queue] = JobCounts(
            active=int(counts.get("active", 0)),
            waiting=int(counts.get("waiting", 0)),
            completed=int(counts.get("completed", 0)),
            failed=int(counts.get("failed", 0)),
            delayed=int(counts.get("delayed", 0)),
            paused=int(counts.get("paused", 0)),
        )
    return result
