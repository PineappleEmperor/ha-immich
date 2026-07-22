"""Constants for the Immich Extras integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "immich_extras"
LOGGER: Final = logging.getLogger(__package__)

UPDATE_INTERVAL: Final = timedelta(seconds=60)

DEFAULT_PORT: Final = 2283

# Immich job queues for which a dedicated "waiting" sensor is created. The
# aggregate job sensors sum across every queue the server reports; these named
# queues are the ones worth surfacing individually.
TRACKED_QUEUES: Final[tuple[str, ...]] = (
    "thumbnailGeneration",
    "metadataExtraction",
    "faceDetection",
    "smartSearch",
    "backupDatabase",
    "library",
)
