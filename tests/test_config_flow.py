"""Config flow tests for Immich Extras."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from aioimmich.exceptions import ImmichUnauthorizedError
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_URL,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.immich_extras.const import DOMAIN

from .conftest import USER_ID

USER_INPUT = {
    CONF_URL: "https://immich.example.com",
    CONF_API_KEY: "secret-key",
    CONF_VERIFY_SSL: True,
}

UNAUTHORIZED = {"message": "Unauthorized", "correlationId": "x"}


async def test_user_flow(hass: HomeAssistant, mock_immich: MagicMock) -> None:
    """A valid submission creates an entry with parsed connection fields."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "immich.example.com"
    assert result["data"] == {
        CONF_HOST: "immich.example.com",
        CONF_PORT: 443,
        CONF_VERIFY_SSL: True,
        CONF_API_KEY: "secret-key",
    }
    assert result["result"].unique_id == USER_ID


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (ImmichUnauthorizedError(UNAUTHORIZED), "invalid_auth"),
        (TimeoutError, "cannot_connect"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    side_effect: Exception,
    expected_error: str,
) -> None:
    """Connection/auth failures surface as form errors and recover."""
    mock_immich.async_setup.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    mock_immich.async_setup.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_invalid_url(
    hass: HomeAssistant, mock_immich: MagicMock
) -> None:
    """A URL with no host is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={**USER_INPUT, CONF_URL: "not-a-url"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_already_configured(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The same account cannot be configured twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reauth updates the stored API key."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == "new-key"


async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfigure updates the connection settings, keeping the API key."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_URL: "http://immich.local:2283", CONF_VERIFY_SSL: False},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_HOST] == "immich.local"
    assert mock_config_entry.data[CONF_PORT] == 2283
    assert mock_config_entry.data[CONF_VERIFY_SSL] is False
    assert mock_config_entry.data[CONF_API_KEY] == "secret-key"


async def test_reconfigure_error(
    hass: HomeAssistant,
    mock_immich: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A connection failure during reconfigure surfaces an error."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    mock_immich.async_setup.side_effect = TimeoutError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_URL: "http://immich.local:2283", CONF_VERIFY_SSL: False},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
