"""Constants for the Immich Extras integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "immich_extras"
LOGGER: Final = logging.getLogger(__package__)

UPDATE_INTERVAL: Final = timedelta(seconds=60)

DEFAULT_PORT: Final = 2283
HTTPS_PORT: Final = 443

# Current config-entry minor version; bumped when stored data gains a field.
ENTRY_MINOR_VERSION: Final = 2

# Stored entry key for the connection scheme (https vs http). Kept separate from
# CONF_VERIFY_SSL, which only controls TLS certificate verification.
CONF_USE_SSL: Final = "use_ssl"

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
