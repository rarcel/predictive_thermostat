"""Privacy regression tests."""

import json

from custom_components.predictive_thermostat.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_whitelist(hass, entry):
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result == {
        "schema_version": 1,
        "observation_only": True,
        "sources_resolved": {
            "indoor_sensor": True,
            "outdoor_sensor": True,
            "heater": True,
        },
    }
    serialized = json.dumps(result)
    for secret in (
        entry.entry_id,
        entry.unique_id,
        entry.title,
        "sensor.inside",
        "switch.heater",
    ):
        assert secret not in serialized
