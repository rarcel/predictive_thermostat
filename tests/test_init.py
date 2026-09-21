"""Lifecycle cleanup and persistent identity."""

from unittest.mock import patch

from homeassistant.helpers import entity_registry as er

from custom_components.predictive_thermostat.const import DOMAIN


async def test_unload_reload(hass, entry, no_services):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("climate", DOMAIN, entry.unique_id)
    with patch(
        "custom_components.predictive_thermostat.climate.ObservationThermostat._refresh"
    ) as refresh:
        assert await hass.config_entries.async_unload(entry.entry_id)
        hass.states.async_set("sensor.inside", "21", {"unit_of_measurement": "°C"})
        registry.async_update_entity("switch.heater", new_entity_id="switch.new_heater")
        await hass.async_block_till_done()
        refresh.assert_not_called()
    assert hass.states.get(entity_id).state == "unavailable"
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("climate", DOMAIN, entry.unique_id) == entity_id
    assert hass.states.get(entity_id).attributes["current_temperature"] == 21
