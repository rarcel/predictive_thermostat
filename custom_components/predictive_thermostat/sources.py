"""Resolve selected sources without using their names as durable identities."""

import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import SOURCE_KEYS


def reference(hass: HomeAssistant, entity_id: str) -> dict[str, str]:
    """Keep registry identity when available, otherwise retain a local reference."""
    registered = er.async_get(hass).async_get(entity_id)
    if registered is None:
        return {"entity_id": entity_id}
    return {
        "domain": registered.domain,
        "platform": registered.platform,
        "unique_id": registered.unique_id,
    }


def resolve(hass: HomeAssistant, source: dict[str, str]) -> str | None:
    """Never bind a removed registered source to an entity reusing its old name."""
    if "unique_id" in source:
        return er.async_get(hass).async_get_entity_id(
            source["domain"], source["platform"], source["unique_id"]
        )
    return source.get("entity_id")


def configured_sources(entry: ConfigEntry) -> dict[str, Any]:
    """Options replace the source selection atomically."""
    return {key: entry.options.get(key, entry.data[key]) for key in SOURCE_KEYS}


def temperature(
    hass: HomeAssistant, entity_id: str | None, target_unit: str
) -> float | None:
    """Read a finite temperature in the requested unit, never perform I/O."""
    if entity_id is None or (state := hass.states.get(entity_id)) is None:
        return None
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    if unit not in (UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT):
        return None
    try:
        value = float(state.state)
        if not math.isfinite(value):
            return None
        converted = float(TemperatureConverter.convert(value, unit, target_unit))
        return converted if math.isfinite(converted) else None
    except TypeError, ValueError:
        return None
