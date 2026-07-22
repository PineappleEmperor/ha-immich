"""Unit tests for the jobs parser."""

from __future__ import annotations

from custom_components.immich_extras.models import JobCounts, parse_jobs

from .conftest import JOBS_PAYLOAD


def test_parse_jobs_full_payload() -> None:
    """A full payload parses every queue into JobCounts."""
    parsed = parse_jobs(JOBS_PAYLOAD)
    assert set(parsed) == {"thumbnailGeneration", "backupDatabase"}
    assert parsed["thumbnailGeneration"] == JobCounts(
        active=1, waiting=3, completed=100, failed=0, delayed=0, paused=0
    )
    assert parsed["backupDatabase"].failed == 2


def test_parse_jobs_missing_fields_default_to_zero() -> None:
    """A queue with a partial jobCounts map defaults missing fields to 0."""
    parsed = parse_jobs({"library": {"jobCounts": {"waiting": 5}}})
    assert parsed["library"] == JobCounts(
        active=0, waiting=5, completed=0, failed=0, delayed=0, paused=0
    )


def test_parse_jobs_empty() -> None:
    """An empty payload yields no queues."""
    assert parse_jobs({}) == {}
