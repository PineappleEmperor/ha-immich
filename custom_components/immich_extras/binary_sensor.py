"""Binary sensor platform for Immich Extras."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .entity import ImmichExtrasEntity

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ImmichExtrasConfigEntry, ImmichExtrasCoordinator
    from .models import ImmichExtrasData


@dataclass(frozen=True, kw_only=True)
class ImmichExtrasBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an Immich Extras binary sensor."""

    value_fn: Callable[[ImmichExtrasData], bool]


COMMON_BINARY_SENSORS: tuple[ImmichExtrasBinarySensorDescription, ...] = (
    ImmichExtrasBinarySensorDescription(
        key="licensed",
        translation_key="licensed",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.licensed,
    ),
)

ADMIN_BINARY_SENSORS: tuple[ImmichExtrasBinarySensorDescription, ...] = (
    ImmichExtrasBinarySensorDescription(
        key="jobs_problem",
        translation_key="jobs_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.jobs is not None
            and any(counts.failed > 0 for counts in data.jobs.values())
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ImmichExtrasConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Immich Extras binary sensors."""
    coordinator = entry.runtime_data
    descriptions = COMMON_BINARY_SENSORS
    if coordinator.is_admin:
        descriptions += ADMIN_BINARY_SENSORS
    async_add_entities(
        ImmichExtrasBinarySensor(coordinator, description)
        for description in descriptions
    )


class ImmichExtrasBinarySensor(ImmichExtrasEntity, BinarySensorEntity):
    """An Immich Extras binary sensor."""

    entity_description: ImmichExtrasBinarySensorDescription

    def __init__(
        self,
        coordinator: ImmichExtrasCoordinator,
        description: ImmichExtrasBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return True when the condition is active."""
        return self.entity_description.value_fn(self.coordinator.data)
