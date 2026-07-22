"""The Immich Extras integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_PORT, Platform

from .const import CONF_USE_SSL, DOMAIN, ENTRY_MINOR_VERSION, HTTPS_PORT
from .coordinator import ImmichExtrasConfigEntry, ImmichExtrasCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: ImmichExtrasConfigEntry
) -> bool:
    """Set up Immich Extras from a config entry."""
    coordinator = ImmichExtrasCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(
    hass: HomeAssistant, entry: ImmichExtrasConfigEntry
) -> bool:
    """Migrate an old config entry."""
    if entry.minor_version < ENTRY_MINOR_VERSION:
        data = {**entry.data}
        # 0.1.0 entries never stored the connection scheme; infer it from the
        # port (https default → https, anything else → http) so existing setups
        # recover.
        data.setdefault(CONF_USE_SSL, data.get(CONF_PORT) == HTTPS_PORT)
        hass.config_entries.async_update_entry(
            entry, data=data, minor_version=ENTRY_MINOR_VERSION
        )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ImmichExtrasConfigEntry
) -> bool:
    """Unload a config entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    entry: ImmichExtrasConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """Allow deletion of a device only once it is gone from the server."""
    coordinator = entry.runtime_data
    server_id = str(entry.unique_id)
    live_ids = {(DOMAIN, server_id)}
    if (stats := coordinator.data.statistics) is not None:
        live_ids.update(
            (DOMAIN, f"{server_id}_user_{user.user_id}")
            for user in stats.usage_by_user
        )
    return not any(identifier in live_ids for identifier in device_entry.identifiers)
