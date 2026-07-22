"""Setup and lifecycle tests for Immich Extras."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.immich_extras import async_remove_config_entry_device
from custom_components.immich_extras.const import DOMAIN

from .conftest import USER_ID


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A config entry sets up to LOADED, creates entities, and unloads."""
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    entities = hass.states.async_entity_ids()
    assert any(e.startswith("sensor.") for e in entities)
    assert any(e.startswith("binary_sensor.") for e in entities)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_two_entries_parallel(
    hass: HomeAssistant, mock_immich: MagicMock
) -> None:
    """Two config entries set up in parallel both reach LOADED."""
    entries = [
        MockConfigEntry(
            domain=DOMAIN,
            title=f"host-{i}",
            unique_id=f"user-{i}",
            data={
                CONF_HOST: f"host-{i}",
                CONF_PORT: 2283,
                CONF_VERIFY_SSL: True,
                CONF_API_KEY: "secret-key",
            },
        )
        for i in range(2)
    ]
    for entry in entries:
        entry.add_to_hass(hass)
    await asyncio.gather(
        *(hass.config_entries.async_setup(entry.entry_id) for entry in entries)
    )
    await hass.async_block_till_done()
    assert all(entry.state is ConfigEntryState.LOADED for entry in entries)


async def test_remove_stale_device(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A device is removable only once its user is gone from the server."""
    await _setup(hass, mock_config_entry)

    live_user = dr.DeviceEntry(
        identifiers={(DOMAIN, f"{USER_ID}_user_{USER_ID}")}, config_entries=set()
    )
    gone_user = dr.DeviceEntry(
        identifiers={(DOMAIN, f"{USER_ID}_user_ghost")}, config_entries=set()
    )
    server = dr.DeviceEntry(
        identifiers={(DOMAIN, USER_ID)}, config_entries=set()
    )

    assert not await async_remove_config_entry_device(
        hass, mock_config_entry, live_user
    )
    assert not await async_remove_config_entry_device(hass, mock_config_entry, server)
    assert await async_remove_config_entry_device(hass, mock_config_entry, gone_user)
