"""Set up a thermostat; importing the pure controller does not require HA."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import DATA_ENTITIES, DOMAIN, SERVICE_RESET_FAULT

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

PLATFORMS = ["climate"]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register the fault acknowledgement action once for all zones."""
    entities = hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTITIES, {})

    async def async_reset_fault(call: ServiceCall) -> None:
        for entity_id in call.data[ATTR_ENTITY_ID]:
            entity = entities.get(entity_id)
            if entity is None:
                raise ServiceValidationError(
                    f"{entity_id} is not a Predictive Thermostat entity"
                )
            await entity.async_reset_fault()

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RESET_FAULT,
        async_reset_fault,
        schema=vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Forward only the climate platform."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the entity and its subscriptions without touching its sources."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
