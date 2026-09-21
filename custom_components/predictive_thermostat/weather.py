"""Home Assistant weather forecast adapter with a conservative fallback."""

from datetime import datetime

from homeassistant.core import HomeAssistant

from .forecast import temperature_at


async def async_forecast_temperature(
    hass: HomeAssistant,
    entity_id: str | None,
    target: datetime,
    fallback: float | None,
) -> float | None:
    """Read an hourly forecast response; any API failure keeps local fallback."""
    if entity_id is None:
        return fallback
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
            return fallback
        return temperature_at(
            [item for item in forecast if isinstance(item, dict)], target, fallback
        )
    except Exception:
        return fallback
