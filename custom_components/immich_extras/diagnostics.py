"""Diagnostics support for Immich Extras."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY, CONF_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import ImmichExtrasConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_HOST, "email", "storage_label"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ImmichExtrasConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return async_redact_data(
        {
            "entry_data": dict(entry.data),
            "is_admin": coordinator.is_admin,
            "data": {
                "licensed": data.licensed,
                "people_count": data.people_count,
                "tags_count": data.tags_count,
                "albums_count": data.albums_count,
                "my_user": asdict(data.my_user),
                "statistics": None
                if data.statistics is None
                else asdict(data.statistics),
                "jobs": None
                if data.jobs is None
                else {queue: asdict(counts) for queue, counts in data.jobs.items()},
            },
        },
        TO_REDACT,
    )
