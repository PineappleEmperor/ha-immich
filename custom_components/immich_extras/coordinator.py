"""Data update coordinator for Immich Extras."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp import ClientError
from aioimmich.exceptions import ImmichForbiddenError, ImmichUnauthorizedError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT, CONF_VERIFY_SSL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ImmichExtrasApi
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL
from .models import ImmichExtrasData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

type ImmichExtrasConfigEntry = ConfigEntry[ImmichExtrasCoordinator]


class ImmichExtrasCoordinator(DataUpdateCoordinator[ImmichExtrasData]):
    """Coordinates polling of the Immich server."""

    config_entry: ImmichExtrasConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: ImmichExtrasConfigEntry
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.api = ImmichExtrasApi(
            async_get_clientsession(hass, config_entry.data[CONF_VERIFY_SSL]),
            config_entry.data[CONF_API_KEY],
            config_entry.data[CONF_HOST],
            config_entry.data[CONF_PORT],
            config_entry.data[CONF_VERIFY_SSL],
        )
        self.is_admin = False

    async def _async_setup(self) -> None:
        """Set up the library and record the account's admin status."""
        try:
            user = await self.api.async_setup()
        except ImmichUnauthorizedError as err:
            raise ConfigEntryAuthFailed from err
        self.is_admin = user.is_admin

    async def _async_update_data(self) -> ImmichExtrasData:
        """Fetch the latest data from the Immich server."""
        try:
            return await self.api.async_get_data(is_admin=self.is_admin)
        except ImmichUnauthorizedError as err:
            raise ConfigEntryAuthFailed from err
        except ImmichForbiddenError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="forbidden"
            ) from err
        except (ClientError, TimeoutError, OSError) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from err
