"""Home Assistant weather forecast adapter with a conservative fallback."""

from dataclasses import dataclass
from datetime import datetime

from homeassistant.core import HomeAssistant

from .forecast import temperature_at


@dataclass(frozen=True)
class ForecastResult:
    """Temperature used by prediction and its explainable source."""

    temperature: float | None
    source: str | None


async def async_forecast_temperature(
    hass: HomeAssistant,
    entity_id: str | None,
    target: datetime,
    fallback: float | None,
) -> ForecastResult:
    """Read an hourly forecast response; any API failure keeps local fallback."""
    if entity_id is None:
        return ForecastResult(fallback, "sensor" if fallback is not None else None)
    try:
        response = await hass.services.async_call(
            "weather",
            "get_forecasts",
            {"entity_id": entity_id, "type": "hourly"},
            blocking=True,
            return_response=True,
        )
        data = response.get(entity_id, response) if isinstance(response, dict) else {}
        forecast = data.get("forecast", []) if isinstance(data, dict) else []
        if not isinstance(forecast, list):
            return ForecastResult(fallback, "sensor" if fallback is not None else None)
        items = [item for item in forecast if isinstance(item, dict)]
        forecast_value = temperature_at(items, target, None)
        if forecast_value is not None:
            return ForecastResult(forecast_value, "forecast")
        return ForecastResult(fallback, "sensor" if fallback is not None else None)
    except Exception:
        return ForecastResult(fallback, "sensor" if fallback is not None else None)
