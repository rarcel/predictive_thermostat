"""UI configuration of arbitrary local sources, without probing the heater."""

from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import ATTR_DEVICE_CLASS, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_HEATER, CONF_INDOOR, CONF_OUTDOOR, DOMAIN, SOURCE_KEYS
from .sources import configured_sources, reference, resolve


def source_schema() -> dict[Any, Any]:
    """Offer domain/device-class selectors; validate existence separately."""
    return {
        vol.Required(key): EntitySelector(
            EntitySelectorConfig(
                filter={"domain": "switch"}
                if key == CONF_HEATER
                else {"domain": "sensor", "device_class": "temperature"}
            )
        )
        for key in SOURCE_KEYS
    }


def validate_sources(
    hass: HomeAssistant, data: dict[str, Any], current_entry_id: str | None = None
) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate references, including registered sources temporarily offline."""
    errors: dict[str, str] = {}
    sources: dict[str, Any] = {}
    registry = er.async_get(hass)
    for key in SOURCE_KEYS:
        entity_id = data[key]
        domain = "switch" if key == CONF_HEATER else "sensor"
        state = hass.states.get(entity_id)
        registered = registry.async_get(entity_id)
        if not entity_id.startswith(f"{domain}.") or (
            state is None and registered is None
        ):
            errors[key] = "invalid_entity"
            continue
        device_class = state.attributes.get(ATTR_DEVICE_CLASS) if state else None
        if registered is not None:
            device_class = (
                registered.device_class
                or registered.original_device_class
                or device_class
            )
        if key != CONF_HEATER and device_class != "temperature":
            errors[key] = "not_temperature"
            continue
        sources[key] = reference(hass, entity_id)
    if data[CONF_INDOOR] == data[CONF_OUTDOOR]:
        errors[CONF_OUTDOOR] = "same_sensor"
    if not errors:
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id == current_entry_id:
                continue
            other = configured_sources(entry)[CONF_HEATER]
            if (
                sources[CONF_HEATER] == other
                or resolve(hass, other) == data[CONF_HEATER]
            ):
                errors[CONF_HEATER] = "heater_in_use"
                break
    return errors, sources


class PredictiveThermostatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one independent observation zone."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select sources without sending any service call."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, sources = validate_sources(self.hass, user_input)
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "empty_name"
            if not errors:
                await self.async_set_unique_id(str(uuid4()))
                return self.async_create_entry(title=name, data=sources)
        schema = vol.Schema({vol.Required(CONF_NAME): str, **source_schema()})
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SourceOptionsFlow:
        """Offer source changes; observation cannot be disabled."""
        return SourceOptionsFlow()


class SourceOptionsFlow(OptionsFlowWithReload):
    """Replace the sources and let HA perform one clean reload."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Keep identity stable across changes of source."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, sources = validate_sources(
                self.hass, user_input, self.config_entry.entry_id
            )
            if not errors:
                return self.async_create_entry(data=sources)
        defaults = {
            key: resolve(self.hass, source)
            for key, source in configured_sources(self.config_entry).items()
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(source_schema()), user_input or defaults
            ),
            errors=errors,
        )
