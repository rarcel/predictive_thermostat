"""Home Assistant adaptation of protected manual and scheduled control."""

import math
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DOMAIN
from .runtime import ControlRuntime


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create exactly one user-facing entity for a zone."""
    async_add_entities([PredictiveThermostat(hass, entry)])


class PredictiveThermostat(ClimateEntity):
    """Expose manual control; all switch decisions go through the runtime."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)}, name=entry.title
        )
        self.runtime = ControlRuntime(hass, entry, self._refresh)
        settings = self.runtime.settings
        self._attr_min_temp = self._display(settings.min_temperature)
        self._attr_max_temp = self._display(settings.max_temperature)
        self._attr_target_temperature_step = settings.target_step * (
            1.8 if self.temperature_unit == UnitOfTemperature.FAHRENHEIT else 1
        )
        self._attr_hvac_mode = HVACMode.OFF

    def _display(self, value: float) -> float:
        return float(
            TemperatureConverter.convert(
                value, UnitOfTemperature.CELSIUS, self.temperature_unit
            )
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self.runtime.start()

    async def async_will_remove_from_hass(self) -> None:
        await self.runtime.stop()
        await super().async_will_remove_from_hass()

    @callback
    def _refresh(self) -> None:
        runtime = self.runtime
        core = runtime.core
        self._attr_current_temperature = (
            self._display(runtime.indoor) if runtime.indoor is not None else None
        )
        self._attr_target_temperature = self._display(runtime.target)
        self._attr_available = runtime.indoor is not None
        self._attr_hvac_mode = HVACMode(runtime.mode)
        self._attr_hvac_action = (
            HVACAction.OFF
            if runtime.settings.observation_only
            else None
            if core.observed is None
            else HVACAction.PREHEATING
            if runtime.preheating and core.observed
            else HVACAction.HEATING
            if core.observed
            else HVACAction.IDLE
            if runtime.heat
            else HVACAction.OFF
        )
        outdoor = (
            self._display(runtime.outdoor) if runtime.outdoor is not None else None
        )
        self._attr_extra_state_attributes = {
            "control_state": "observation"
            if runtime.settings.observation_only
            else runtime.decision.state,
            "observation_only": runtime.settings.observation_only,
            "outdoor_temperature": outdoor,
            "heater_available": core.observed is not None,
            "fault_reason": core.fault,
            "pending_command": "on"
            if core.pending is True
            else "off"
            if core.pending is False
            else None,
            "fallback_reason": (
                "indoor_unavailable"
                if runtime.indoor is None
                else "outdoor_unavailable"
                if outdoor is None
                else "heater_unavailable"
                if core.observed is None
                else None
            ),
            "schedule_target_temperature": self._display(
                runtime.schedule_resolution.current.temperature
            )
            if runtime.schedule_resolution is not None
            else None,
            "next_target_temperature": self._display(
                runtime.schedule_resolution.next.temperature
            )
            if runtime.schedule_resolution is not None
            else None,
            "next_target_time": runtime.schedule_resolution.next_at.isoformat()
            if runtime.schedule_resolution is not None
            else None,
            "override_until": runtime.override[1].isoformat()
            if runtime.override is not None
            else None,
            "predicted_start_time": runtime.predicted_start.isoformat()
            if runtime.predicted_start is not None
            else None,
            "predicted_heating_minutes": runtime.prediction.minutes
            if runtime.prediction is not None
            else None,
            "prediction_confidence": runtime.prediction.confidence
            if runtime.prediction is not None
            else 0.0,
            "prediction_reason": runtime.prediction.reason
            if runtime.prediction is not None
            else "outdoor_unavailable"
            if runtime.mode == "auto" and runtime.outdoor is None
            else None,
            "learning_samples": runtime.learning.samples,
            "last_prediction_error_minutes": runtime.learning.mean_arrival_error,
        }
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in (HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO):
            raise ServiceValidationError("Only OFF, HEAT and AUTO are supported")
        self.runtime.set_mode(hvac_mode.value)
        self._refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        value = kwargs.get("temperature")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ServiceValidationError("A finite target temperature is required")
        target = float(
            TemperatureConverter.convert(
                value, self.temperature_unit, UnitOfTemperature.CELSIUS
            )
        )
        settings = self.runtime.settings
        if (
            not math.isfinite(target)
            or not settings.min_temperature <= target <= settings.max_temperature
        ):
            raise ServiceValidationError("Target temperature outside configured limits")
        mode = kwargs.get("hvac_mode")
        if mode is not None and mode not in (
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.AUTO,
        ):
            raise ServiceValidationError("Only OFF, HEAT and AUTO are supported")
        if mode is not None:
            self.runtime.set_mode(mode.value)
        self.runtime.set_target(target)
        self._refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
