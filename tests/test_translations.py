"""Verify every translation_key used in code resolves in strings.json."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.immich_extras import binary_sensor, sensor

STRINGS = json.loads(
    (Path(sensor.__file__).parent / "strings.json").read_text(encoding="utf-8")
)


def test_sensor_translation_keys_resolve() -> None:
    """Each sensor translation_key exists under entity.sensor."""
    defined = set(STRINGS["entity"]["sensor"])
    used = {
        desc.translation_key
        for desc in (*sensor.COMMON_SENSORS, *sensor.ADMIN_SENSORS, *sensor._queue_sensors())
    } | {desc.translation_key for desc in sensor.USER_SENSORS}
    assert used <= defined, f"missing sensor translations: {used - defined}"


def test_binary_sensor_translation_keys_resolve() -> None:
    """Each binary_sensor translation_key exists under entity.binary_sensor."""
    defined = set(STRINGS["entity"]["binary_sensor"])
    used = {
        desc.translation_key
        for desc in (
            *binary_sensor.COMMON_BINARY_SENSORS,
            *binary_sensor.ADMIN_BINARY_SENSORS,
        )
    }
    assert used <= defined, f"missing binary_sensor translations: {used - defined}"


def test_icons_resolve() -> None:
    """Each entity translation_key has an icon entry."""
    icons = json.loads(
        (Path(sensor.__file__).parent / "icons.json").read_text(encoding="utf-8")
    )
    for platform, section in (
        ("sensor", (*sensor.COMMON_SENSORS, *sensor.ADMIN_SENSORS, *sensor._queue_sensors(), *sensor.USER_SENSORS)),
        (
            "binary_sensor",
            (*binary_sensor.COMMON_BINARY_SENSORS, *binary_sensor.ADMIN_BINARY_SENSORS),
        ),
    ):
        defined = set(icons["entity"][platform])
        used = {desc.translation_key for desc in section}
        assert used <= defined, f"missing {platform} icons: {used - defined}"
