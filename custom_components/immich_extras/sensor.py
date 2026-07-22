"""Sensor platform for Immich Extras."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfInformation
from homeassistant.helpers.typing import StateType

from .const import TRACKED_QUEUES
from .entity import ImmichExtrasEntity, ImmichExtrasUserEntity

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from aioimmich.server.models import ByUserUsage
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ImmichExtrasConfigEntry, ImmichExtrasCoordinator
    from .models import ImmichExtrasData


def _quota_pct(usage: int | None, size: int | None) -> float | None:
    """Return quota usage as a percentage, or None when no quota is set."""
    if not size or usage is None:
        return None
    return round(usage / size * 100, 2)


@dataclass(frozen=True, kw_only=True)
class ImmichExtrasSensorDescription(SensorEntityDescription):
    """Describes a server-scoped Immich Extras sensor."""

    value_fn: Callable[[ImmichExtrasData], StateType]


@dataclass(frozen=True, kw_only=True)
class ImmichExtrasUserSensorDescription(SensorEntityDescription):
    """Describes a per-user Immich Extras sensor."""

    value_fn: Callable[[ByUserUsage], StateType]


COMMON_SENSORS: tuple[ImmichExtrasSensorDescription, ...] = (
    ImmichExtrasSensorDescription(
        key="people_count",
        translation_key="people_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.people_count,
    ),
    ImmichExtrasSensorDescription(
        key="tags_count",
        translation_key="tags_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.tags_count,
    ),
    ImmichExtrasSensorDescription(
        key="albums_count",
        translation_key="albums_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.albums_count,
    ),
    ImmichExtrasSensorDescription(
        key="my_quota_size",
        translation_key="my_quota_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.my_user.quota_size_in_bytes,
    ),
    ImmichExtrasSensorDescription(
        key="my_quota_usage",
        translation_key="my_quota_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.my_user.quota_usage_in_bytes,
    ),
    ImmichExtrasSensorDescription(
        key="my_quota_pct",
        translation_key="my_quota_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _quota_pct(
            data.my_user.quota_usage_in_bytes, data.my_user.quota_size_in_bytes
        ),
    ),
)

ADMIN_SENSORS: tuple[ImmichExtrasSensorDescription, ...] = (
    ImmichExtrasSensorDescription(
        key="total_usage",
        translation_key="total_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            None if data.statistics is None else data.statistics.usage
        ),
    ),
    ImmichExtrasSensorDescription(
        key="jobs_active",
        translation_key="jobs_active",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            None
            if data.jobs is None
            else sum(counts.active for counts in data.jobs.values())
        ),
    ),
    ImmichExtrasSensorDescription(
        key="jobs_waiting",
        translation_key="jobs_waiting",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            None
            if data.jobs is None
            else sum(counts.waiting for counts in data.jobs.values())
        ),
    ),
    ImmichExtrasSensorDescription(
        key="jobs_failed",
        translation_key="jobs_failed",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            None
            if data.jobs is None
            else sum(counts.failed for counts in data.jobs.values())
        ),
    ),
)


def _queue_waiting(data: ImmichExtrasData, queue: str) -> StateType:
    """Return the waiting count for a single queue."""
    if data.jobs is None or (counts := data.jobs.get(queue)) is None:
        return None
    return counts.waiting


def _queue_sensors() -> tuple[ImmichExtrasSensorDescription, ...]:
    """Build a waiting sensor description per tracked queue."""
    return tuple(
        ImmichExtrasSensorDescription(
            key=f"queue_{queue}_waiting",
            translation_key=f"queue_{queue.lower()}_waiting",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda data, q=queue: _queue_waiting(data, q),
        )
        for queue in TRACKED_QUEUES
    )


USER_SENSORS: tuple[ImmichExtrasUserSensorDescription, ...] = (
    ImmichExtrasUserSensorDescription(
        key="user_photos",
        translation_key="user_photos",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda usage: usage.photos,
    ),
    ImmichExtrasUserSensorDescription(
        key="user_videos",
        translation_key="user_videos",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda usage: usage.videos,
    ),
    ImmichExtrasUserSensorDescription(
        key="user_usage",
        translation_key="user_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda usage: usage.usage,
    ),
    ImmichExtrasUserSensorDescription(
        key="user_quota",
        translation_key="user_quota",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        suggested_display_precision=2,
        value_fn=lambda usage: usage.quota_size_in_bytes,
    ),
    ImmichExtrasUserSensorDescription(
        key="user_quota_pct",
        translation_key="user_quota_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda usage: _quota_pct(usage.usage, usage.quota_size_in_bytes),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ImmichExtrasConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Immich Extras sensors."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        ImmichExtrasSensor(coordinator, description) for description in COMMON_SENSORS
    ]
    if coordinator.is_admin:
        entities.extend(
            ImmichExtrasSensor(coordinator, description)
            for description in (*ADMIN_SENSORS, *_queue_sensors())
        )
    async_add_entities(entities)

    if coordinator.is_admin:
        _setup_user_sensors(coordinator, async_add_entities)


def _setup_user_sensors(
    coordinator: ImmichExtrasCoordinator,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add per-user sensors, creating new ones as users appear."""
    known: set[str] = set()

    def _add_new_users() -> None:
        stats = coordinator.data.statistics
        if stats is None:
            return
        new_entities: list[SensorEntity] = []
        for usage in stats.usage_by_user:
            if usage.user_id in known:
                continue
            known.add(usage.user_id)
            new_entities.extend(
                ImmichExtrasUserSensor(
                    coordinator, usage.user_id, usage.user_name, description
                )
                for description in USER_SENSORS
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_users()
    coordinator.config_entry.async_on_unload(
        coordinator.async_add_listener(_add_new_users)
    )


class ImmichExtrasSensor(ImmichExtrasEntity, SensorEntity):
    """A server-scoped Immich Extras sensor."""

    entity_description: ImmichExtrasSensorDescription

    def __init__(
        self,
        coordinator: ImmichExtrasCoordinator,
        description: ImmichExtrasSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)


class ImmichExtrasUserSensor(ImmichExtrasUserEntity, SensorEntity):
    """A per-user Immich Extras sensor."""

    entity_description: ImmichExtrasUserSensorDescription

    def __init__(
        self,
        coordinator: ImmichExtrasCoordinator,
        user_id: str,
        user_name: str,
        description: ImmichExtrasUserSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, user_id, user_name, description.key)
        self.entity_description = description

    def _usage(self) -> ByUserUsage | None:
        """Return this user's usage record from the latest data."""
        stats = self.coordinator.data.statistics
        if stats is None:
            return None
        return next(
            (u for u in stats.usage_by_user if u.user_id == self._user_id), None
        )

    @property
    def available(self) -> bool:
        """Return True only while the user still exists on the server."""
        return super().available and self._usage() is not None

    @property
    def native_value(self) -> StateType:
        """Return the current value."""
        if (usage := self._usage()) is None:
            return None
        return self.entity_description.value_fn(usage)
