"""Base entities for Immich Extras."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import ImmichExtrasCoordinator


class ImmichExtrasEntity(CoordinatorEntity["ImmichExtrasCoordinator"]):
    """Base entity attached to the Immich server device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ImmichExtrasCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        server_id = coordinator.config_entry.unique_id
        self._attr_unique_id = f"{server_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(server_id))},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Immich",
            name=coordinator.config_entry.title,
        )


class ImmichExtrasUserEntity(CoordinatorEntity["ImmichExtrasCoordinator"]):
    """Base entity attached to a per-user device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ImmichExtrasCoordinator,
        user_id: str,
        user_name: str,
        key: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._user_id = user_id
        server_id = coordinator.config_entry.unique_id
        self._attr_unique_id = f"{server_id}_user_{user_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{server_id}_user_{user_id}")},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Immich",
            model="User",
            name=user_name,
            via_device=(DOMAIN, str(server_id)),
        )
