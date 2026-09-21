"""Independent zones and persistence through configuration serialization."""

import json

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.predictive_thermostat.const import CONF_HEATER, DOMAIN


async def test_independent_zones(hass, entry, no_services):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # The second zone uses unregistered sources from another hypothetical integration.
    hass.states.async_set("sensor.room_b", "70", {"unit_of_measurement": "°F"})
    hass.states.async_set("sensor.garden_b", "40", {"unit_of_measurement": "°F"})
    hass.states.async_set("switch.boiler_b", "on")
    second = MockConfigEntry(
        domain=DOMAIN,
        title="Another zone",
        unique_id="another-stable-identity",
        data={
            "indoor_sensor": {"entity_id": "sensor.room_b"},
            "outdoor_sensor": {"entity_id": "sensor.garden_b"},
            "heater": {"entity_id": "switch.boiler_b"},
        },
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    first_id = registry.async_get_entity_id("climate", DOMAIN, entry.unique_id)
    second_id = registry.async_get_entity_id("climate", DOMAIN, second.unique_id)
    assert first_id != second_id
    assert len(hass.states.async_entity_ids("climate")) == 2
    hass.states.async_set("sensor.room_b", "77", {"unit_of_measurement": "°F"})
    await hass.async_block_till_done()
    assert hass.states.get(second_id).attributes["current_temperature"] == 25
    assert hass.states.get(first_id).attributes["current_temperature"] == 20
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(second_id).state == "off"
    assert hass.states.get("switch.boiler_b").state == "on"


async def test_serialized_entry_restores_sources(hass, inputs, no_services):
    # A new entry object receives JSON data as it would after HA reloads storage.
    data = json.loads(
        json.dumps(
            {
                "indoor_sensor": {
                    "domain": "sensor",
                    "platform": "test",
                    "unique_id": "inside",
                },
                "outdoor_sensor": {
                    "domain": "sensor",
                    "platform": "test",
                    "unique_id": "outside",
                },
                CONF_HEATER: {
                    "domain": "switch",
                    "platform": "test",
                    "unique_id": "heater",
                },
            }
        )
    )
    registry = er.async_get(hass)
    registry.async_update_entity("sensor.inside", new_entity_id="sensor.new_name")
    hass.states.async_set("sensor.new_name", "24", {"unit_of_measurement": "°C"})
    restored = MockConfigEntry(
        domain=DOMAIN, title="Restored", unique_id="persisted", data=data
    )
    restored.add_to_hass(hass)
    assert await hass.config_entries.async_setup(restored.entry_id)
    await hass.async_block_till_done()
    entity_id = registry.async_get_entity_id("climate", DOMAIN, "persisted")
    assert hass.states.get(entity_id).attributes["current_temperature"] == 24
