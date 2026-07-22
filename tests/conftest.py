"""Fixtures for Immich Extras tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioimmich.server.models import ImmichServerAbout, ImmichServerStatistics
from aioimmich.users.models import ImmichUserObject
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT, CONF_VERIFY_SSL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.immich_extras.const import DOMAIN

USER_ID = "user-1"


def build_user(*, is_admin: bool, user_id: str = USER_ID) -> ImmichUserObject:
    """Build an ImmichUserObject from a representative API payload."""
    return ImmichUserObject.from_dict(
        {
            "id": user_id,
            "name": "Admin" if is_admin else "Viewer",
            "email": "admin@example.com",
            "avatarColor": "primary",
            "profileChangedAt": "2024-01-01T00:00:00.000Z",
            "profileImagePath": "",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "isAdmin": is_admin,
            "oauthId": "",
            "shouldChangePassword": False,
            "status": "active",
            "storageLabel": "",
            "deletedAt": None,
            "quotaSizeInBytes": 100_000_000_000,
            "quotaUsageInBytes": 25_000_000_000,
            "updatedAt": None,
        }
    )


def build_statistics(user_ids: list[str] | None = None) -> ImmichServerStatistics:
    """Build server statistics with one usage record per given user id."""
    ids = user_ids if user_ids is not None else [USER_ID, "user-2"]
    return ImmichServerStatistics.from_dict(
        {
            "photos": 100,
            "videos": 20,
            "usage": 5_000_000_000,
            "usagePhotos": 4_000_000_000,
            "usageVideos": 1_000_000_000,
            "usageByUser": [
                {
                    "userId": uid,
                    "userName": f"User {uid}",
                    "photos": 50,
                    "videos": 10,
                    "usage": 2_500_000_000,
                    "usagePhotos": 2_000_000_000,
                    "usageVideos": 500_000_000,
                    "quotaSizeInBytes": 50_000_000_000,
                }
                for uid in ids
            ],
        }
    )


def build_about() -> ImmichServerAbout:
    """Build server about info."""
    return ImmichServerAbout.from_dict(
        {"licensed": True, "version": "1.140.0", "versionUrl": ""}
    )


JOBS_PAYLOAD = {
    "thumbnailGeneration": {
        "jobCounts": {
            "active": 1,
            "waiting": 3,
            "completed": 100,
            "failed": 0,
            "delayed": 0,
            "paused": 0,
        },
        "queueStatus": {"isActive": True, "isPaused": False},
    },
    "backupDatabase": {
        "jobCounts": {
            "active": 0,
            "waiting": 0,
            "completed": 5,
            "failed": 2,
            "delayed": 0,
            "paused": 0,
        },
        "queueStatus": {"isActive": False, "isPaused": False},
    },
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of the custom integration in every test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="immich.example.com",
        unique_id=USER_ID,
        data={
            CONF_HOST: "immich.example.com",
            CONF_PORT: 2283,
            CONF_VERIFY_SSL: True,
            CONF_API_KEY: "secret-key",
        },
    )


def _build_immich_mock(*, is_admin: bool) -> MagicMock:
    """Build a mocked aioimmich.Immich client."""
    client = MagicMock()
    client.async_setup = AsyncMock()
    client.users.async_get_my_user = AsyncMock(
        return_value=build_user(is_admin=is_admin)
    )
    client.server.async_get_about_info = AsyncMock(return_value=build_about())
    client.server.async_get_server_statistics = AsyncMock(
        return_value=build_statistics()
    )
    client.people.async_get_people_count = AsyncMock(return_value=7)
    client.tags.async_get_all_tags = AsyncMock(return_value=[MagicMock(), MagicMock()])
    client.albums.async_get_all_albums = AsyncMock(return_value=[MagicMock()])
    client.api.async_do_request = AsyncMock(return_value=JOBS_PAYLOAD)
    return client


@pytest.fixture
def mock_immich() -> Generator[MagicMock]:
    """Patch aioimmich.Immich with an admin client."""
    client = _build_immich_mock(is_admin=True)
    with patch(
        "custom_components.immich_extras.api.Immich", return_value=client
    ) as immich:
        immich.client = client
        yield client


@pytest.fixture
def mock_immich_non_admin() -> Generator[MagicMock]:
    """Patch aioimmich.Immich with a non-admin client."""
    client = _build_immich_mock(is_admin=False)
    with patch("custom_components.immich_extras.api.Immich", return_value=client):
        yield client
