"""Private, versioned write-ahead record for restart-safe heater control."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN


class ControlStore(Store[dict[str, Any]]):
    """A pending command survives a crash as an explicit fault, never a retry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        super().__init__(
            hass, 2, f"{DOMAIN}.{entry_id}.control", private=True, atomic_writes=True
        )

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Keep V1 safety records; later formats must migrate explicitly."""
        if old_major_version == 1:
            return old_data
        raise ValueError("Unsupported control storage version")
