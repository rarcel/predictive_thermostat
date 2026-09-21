"""Diagnostics assembled from a whitelist, excluding private source references."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .sources import configured_sources, resolve


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return structural information only; never copy entry data wholesale."""
    return {
        "schema_version": entry.version,
        "observation_only": entry.options.get("settings", {}).get(
            "observation_only", True
        ),
        "forecast_configured": "weather_entity" in entry.options,
        "optimal_stop_enabled": entry.options.get("settings", {}).get(
            "optimal_stop_enabled", False
        ),
        "sources_resolved": {
            role: resolve(hass, ref) is not None
            for role, ref in configured_sources(entry).items()
        },
    }
