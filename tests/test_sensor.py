"""Sensor and binary-sensor tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.immich_extras.const import DOMAIN

from .conftest import USER_ID, build_statistics
from .test_init import _setup


def _state(hass: HomeAssistant, unique_id: str, platform: str = "sensor") -> str | None:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, f"no entity for {unique_id}"
    state = hass.states.get(entity_id)
    return state.state if state else None


async def test_common_sensors(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Count and my-account sensors report the expected values."""
    await _setup(hass, mock_config_entry)
    assert _state(hass, f"{USER_ID}_people_count") == "7"
    assert _state(hass, f"{USER_ID}_tags_count") == "2"
    assert _state(hass, f"{USER_ID}_albums_count") == "1"
    assert _state(hass, f"{USER_ID}_my_quota_pct") == "25.0"


async def test_admin_sensors(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Admin job and total-usage sensors report the expected values."""
    await _setup(hass, mock_config_entry)
    assert _state(hass, f"{USER_ID}_jobs_active") == "1"
    assert _state(hass, f"{USER_ID}_jobs_waiting") == "3"
    assert _state(hass, f"{USER_ID}_jobs_failed") == "2"
    assert _state(hass, f"{USER_ID}_queue_thumbnailGeneration_waiting") == "3"
    assert (
        _state(hass, f"{USER_ID}_jobs_problem", "binary_sensor") == "on"
    )
    assert _state(hass, f"{USER_ID}_licensed", "binary_sensor") == "on"


async def test_data_size_device_class(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The usage sensor locks its DATA_SIZE device_class and MEASUREMENT state_class."""
    await _setup(hass, mock_config_entry)
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{USER_ID}_total_usage"
    )
    state = hass.states.get(entity_id)
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.DATA_SIZE
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT


async def test_per_user_sensors(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Per-user sensors are created per usage record."""
    await _setup(hass, mock_config_entry)
    assert _state(hass, f"{USER_ID}_user_{USER_ID}_user_photos") == "50"
    assert _state(hass, f"{USER_ID}_user_{USER_ID}_user_quota_pct") == "5.0"
    assert _state(hass, f"{USER_ID}_user_user-2_user_videos") == "10"


async def test_non_admin_has_no_admin_entities(
    hass: HomeAssistant,
    mock_immich_non_admin: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A non-admin key exposes only the common entities."""
    await _setup(hass, mock_config_entry)
    registry = er.async_get(hass)
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{USER_ID}_jobs_active")
        is None
    )
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{USER_ID}_user_{USER_ID}_user_photos")
        is None
    )
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{USER_ID}_people_count")
        is not None
    )


async def test_dynamic_user_add_and_remove(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A user appearing later gets entities; a removed user goes unavailable."""
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data

    # Add a third user.
    mock_immich.server.async_get_server_statistics.return_value = build_statistics(
        [USER_ID, "user-2", "user-3"]
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, f"{USER_ID}_user_user-3_user_photos") == "50"

    # Remove user-2.
    mock_immich.server.async_get_server_statistics.return_value = build_statistics(
        [USER_ID, "user-3"]
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, f"{USER_ID}_user_user-2_user_videos") == "unavailable"
