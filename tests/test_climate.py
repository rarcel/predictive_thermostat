"""Exercise state changes and command rejection on the real HA platform."""

import pytest
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.predictive_thermostat.const import DOMAIN


async def loaded(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return er.async_get(hass).async_get_entity_id("climate", DOMAIN, entry.unique_id)


async def test_observation(hass, entry, no_services):
    entity_id = await loaded(hass, entry)
    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert state.attributes["hvac_modes"] == ["off"]
    assert state.attributes["supported_features"] == 0
    assert state.attributes["current_temperature"] == 20
    assert state.attributes["outdoor_temperature"] == 8
    assert state.attributes["control_state"] == "observation"
    hass.states.async_set("switch.heater", "on")
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["hvac_action"] == "off"
    assert len(hass.states.async_entity_ids(CLIMATE_DOMAIN)) == 1


@pytest.mark.parametrize(
    "value,unit",
    [
        ("unavailable", "°C"),
        ("unknown", "°C"),
        ("nan", "°C"),
        ("inf", "°C"),
        ("20", "%"),
    ],
)
async def test_invalid_inside_recovers(hass, entry, value, unit, no_services):
    entity_id = await loaded(hass, entry)
    hass.states.async_set("sensor.inside", value, {"unit_of_measurement": unit})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unavailable"
    hass.states.async_set("sensor.inside", "68", {"unit_of_measurement": "°F"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"
    assert hass.states.get(entity_id).attributes["current_temperature"] == 20


async def test_fahrenheit_display(hass, entry, no_services):
    hass.config.units = US_CUSTOMARY_SYSTEM
    entity_id = await loaded(hass, entry)
    assert hass.states.get(entity_id).attributes["current_temperature"] == 68
    assert hass.states.get(entity_id).attributes[
        "outdoor_temperature"
    ] == pytest.approx(46.4)


async def test_conversion_overflow_is_unavailable(hass, entry, no_services):
    hass.config.units = US_CUSTOMARY_SYSTEM
    entity_id = await loaded(hass, entry)
    hass.states.async_set("sensor.inside", "1.7e308", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unavailable"


async def test_source_rename_and_removal(hass, entry, no_services):
    entity_id = await loaded(hass, entry)
    registry = er.async_get(hass)
    registry.async_update_entity("sensor.inside", new_entity_id="sensor.renamed")
    hass.states.async_set("sensor.renamed", "23", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["current_temperature"] == 23
    registry.async_remove("sensor.renamed")
    hass.states.async_set("sensor.inside", "99", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unavailable"


async def test_missing_outdoor_and_heater(hass, entry, no_services):
    entity_id = await loaded(hass, entry)
    hass.states.async_set("sensor.outside", "unavailable")
    hass.states.async_set("switch.heater", "unavailable")
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert state.attributes["outdoor_temperature"] is None
    assert not state.attributes["heater_available"]
    assert state.attributes["fallback_reason"] == "outdoor_unavailable"


async def test_services_cannot_control_heater(hass, entry):
    entity_id = await loaded(hass, entry)
    # Dummy switch services detect commands while climate services run normally.
    calls = []

    async def record(call):
        calls.append(call)

    for service in ("turn_on", "turn_off", "toggle"):
        hass.services.async_register("switch", service, record)
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "off"},
        blocking=True,
    )
    for service, data in [
        ("set_hvac_mode", {"hvac_mode": "heat"}),
        ("set_temperature", {"temperature": 25}),
        ("turn_on", {}),
        ("turn_off", {}),
    ]:
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "climate", service, {"entity_id": entity_id, **data}, blocking=True
            )
    assert not calls
    assert hass.states.get("switch.heater").state == "off"
