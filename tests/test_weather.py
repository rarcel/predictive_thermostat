"""Forecast service failures are always conservative fallbacks."""

from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from custom_components.predictive_thermostat.weather import async_forecast_temperature


class FakeHass:
    def __init__(self, response=None, error=None):
        self.services = type(
            "Services",
            (),
            {"async_call": AsyncMock(side_effect=error, return_value=response)},
        )()


async def test_weather_response_and_fallbacks():
    target = datetime(2026, 9, 21, 8, tzinfo=ZoneInfo("Europe/Paris"))
    hass = FakeHass(
        {
            "weather.test": {
                "forecast": [
                    {"datetime": "2026-09-21T08:00:00+02:00", "temperature": 4}
                ]
            }
        }
    )
    forecast = await async_forecast_temperature(hass, "weather.test", target, 8)
    assert (forecast.temperature, forecast.source) == (4, "forecast")
    fallback = await async_forecast_temperature(FakeHass(), None, target, 8)
    assert (fallback.temperature, fallback.source) == (8, "sensor")
    failed = await async_forecast_temperature(
        FakeHass(error=RuntimeError()), "weather.test", target, 8
    )
    assert (failed.temperature, failed.source) == (8, "sensor")
