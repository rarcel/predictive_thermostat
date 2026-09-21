from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.predictive_thermostat.forecast import temperature_at


def test_forecast_uses_nearest_valid_point_or_fallback():
    zone = ZoneInfo("Europe/Paris")
    target = datetime(2026, 9, 21, 8, tzinfo=zone)
    assert (
        temperature_at(
            [{"datetime": "2026-09-21T09:00:00+02:00", "temperature": 4}], target, 8
        )
        == 4
    )
    assert temperature_at([], target, 8) == 8
    assert temperature_at([{"datetime": "bad", "temperature": 1}], target, 8) == 8
