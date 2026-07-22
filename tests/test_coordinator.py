"""Coordinator behaviour tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from aioimmich.exceptions import ImmichUnauthorizedError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .test_init import _setup


async def test_non_admin_skips_admin_data(
    hass: HomeAssistant,
    mock_immich_non_admin: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A non-admin key never calls the admin-only endpoints."""
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    mock_immich_non_admin.server.async_get_server_statistics.assert_not_called()
    mock_immich_non_admin.api.async_do_request.assert_not_called()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.is_admin is False
    assert coordinator.data.statistics is None
    assert coordinator.data.jobs is None
    # Per-user and job entities must not exist for a non-admin key.
    assert hass.states.get("sensor.host_0_jobs_active") is None


async def test_admin_fetches_all(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An admin key fetches statistics and jobs."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    assert coordinator.is_admin is True
    assert coordinator.data.statistics is not None
    assert coordinator.data.jobs is not None
    mock_immich.server.async_get_server_statistics.assert_called()
    mock_immich.api.async_do_request.assert_called_with("jobs")


async def test_auth_failure_triggers_reauth(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An auth error during setup starts a reauth flow."""
    mock_immich.async_setup.side_effect = ImmichUnauthorizedError(
        {"message": "Unauthorized", "correlationId": "x"}
    )
    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress()
    assert any(flow["context"]["source"] == "reauth" for flow in flows)
