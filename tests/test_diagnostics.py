"""Diagnostics tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from .test_init import _setup


async def test_diagnostics_shape_and_redaction(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics expose the data shape and redact secrets."""
    await _setup(hass, mock_config_entry)
    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert result["is_admin"] is True
    assert result["data"]["people_count"] == 7
    assert result["data"]["statistics"] is not None
    assert result["data"]["jobs"]["backupDatabase"]["failed"] == 2

    assert result["entry_data"][CONF_API_KEY] == "**REDACTED**"
    assert result["entry_data"][CONF_HOST] == "**REDACTED**"
    assert result["data"]["my_user"]["email"] == "**REDACTED**"
