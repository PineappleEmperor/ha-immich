"""Config flow for Immich Extras."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import voluptuous as vol
from aiohttp import ClientError
from aioimmich.exceptions import ImmichUnauthorizedError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_URL,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ImmichExtrasApi
from .const import CONF_USE_SSL, DEFAULT_PORT, DOMAIN, ENTRY_MINOR_VERSION

if TYPE_CHECKING:
    from collections.abc import Mapping

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)


def _parse_url(url: str) -> tuple[str, int, bool]:
    """Split a user-entered URL into host, port and SSL flag."""
    parsed = urlparse(url)
    if parsed.hostname is None:
        raise ValueError("invalid_url")
    use_ssl = parsed.scheme == "https"
    port = parsed.port or (443 if use_ssl else DEFAULT_PORT)
    return parsed.hostname, port, use_ssl


class ImmichExtrasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Immich Extras config flow."""

    MINOR_VERSION = ENTRY_MINOR_VERSION

    async def _validate(
        self, host: str, port: int, use_ssl: bool, api_key: str
    ) -> str:
        """Connect to the server and return the authenticated user id."""
        api = ImmichExtrasApi(
            async_get_clientsession(self.hass, use_ssl), api_key, host, port, use_ssl
        )
        user = await api.async_setup()
        return user.user_id

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                host, port, use_ssl = _parse_url(user_input[CONF_URL])
            except ValueError:
                errors["base"] = "invalid_url"
            else:
                try:
                    user_id = await self._validate(
                        host, port, use_ssl, user_input[CONF_API_KEY]
                    )
                except ImmichUnauthorizedError:
                    errors["base"] = "invalid_auth"
                except (ClientError, TimeoutError, OSError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(user_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=host,
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_USE_SSL: use_ssl,
                            CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                            CONF_API_KEY: user_input[CONF_API_KEY],
                        },
                    )
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with a new API key."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                user_id = await self._validate(
                    entry.data[CONF_HOST],
                    entry.data[CONF_PORT],
                    entry.data[CONF_VERIFY_SSL],
                    user_input[CONF_API_KEY],
                )
            except ImmichUnauthorizedError:
                errors["base"] = "invalid_auth"
            except (ClientError, TimeoutError, OSError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: user_input[CONF_API_KEY]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the connection settings."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            try:
                host, port, use_ssl = _parse_url(user_input[CONF_URL])
            except ValueError:
                errors["base"] = "invalid_url"
            else:
                try:
                    user_id = await self._validate(
                        host, port, use_ssl, entry.data[CONF_API_KEY]
                    )
                except ImmichUnauthorizedError:
                    errors["base"] = "invalid_auth"
                except (ClientError, TimeoutError, OSError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(user_id)
                    self._abort_if_unique_id_mismatch(reason="wrong_account")
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_USE_SSL: use_ssl,
                            CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                        },
                    )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Required(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            errors=errors,
        )
