"""Configuration never probes hardware and validates arbitrary sources."""

from unittest.mock import patch

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.predictive_thermostat.const import (
    CONF_HEATER,
    CONF_INDOOR,
    CONF_OUTDOOR,
    DOMAIN,
)
from custom_components.predictive_thermostat.settings import Settings


async def test_user_flow(hass, inputs, no_services):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    with patch(
        "custom_components.predictive_thermostat.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], inputs
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test zone"
    assert result["result"].unique_id
    assert result["data"][CONF_HEATER] == {
        "domain": "switch",
        "platform": "test",
        "unique_id": "heater",
    }


@pytest.mark.parametrize(
    "key,value,error",
    [
        (CONF_NAME, "  ", "empty_name"),
        (CONF_INDOOR, "sensor.missing", "invalid_entity"),
        (CONF_OUTDOOR, "sensor.inside", "same_sensor"),
        (CONF_HEATER, "switch.missing", "invalid_entity"),
        (CONF_HEATER, "sensor.inside", "invalid_entity"),
    ],
)
async def test_invalid_input(hass, inputs, key, value, error, no_services):
    inputs[key] = value
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=inputs
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"][key] == error


async def test_wrong_device_class(hass, inputs, no_services):
    hass.states.async_set("sensor.humidity", "50", {"device_class": "humidity"})
    inputs[CONF_INDOOR] = "sensor.humidity"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=inputs
    )
    assert result["errors"][CONF_INDOOR] == "not_temperature"


async def test_registered_offline_sources_allowed(hass, inputs, no_services):
    for key in (CONF_INDOOR, CONF_OUTDOOR, CONF_HEATER):
        hass.states.async_remove(inputs[key])
    with patch(
        "custom_components.predictive_thermostat.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=inputs
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_after_rename(hass, inputs, entry, no_services):
    er.async_get(hass).async_update_entity(
        "switch.heater", new_entity_id="switch.renamed"
    )
    inputs[CONF_HEATER] = "switch.renamed"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=inputs
    )
    assert result["errors"][CONF_HEATER] == "heater_in_use"


async def test_options_reload(hass, inputs, entry, no_services):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("climate", DOMAIN, entry.unique_id)
    hass.states.async_set(
        "sensor.replacement",
        "22",
        {"device_class": "temperature", "unit_of_measurement": "°C"},
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_INDOOR: "sensor.replacement",
                CONF_OUTDOOR: inputs[CONF_OUTDOOR],
                CONF_HEATER: inputs[CONF_HEATER],
                **Settings().as_dict(),
                "reset_fault": False,
            },
        )
        await hass.async_block_till_done()
        reload.assert_awaited_once_with(entry.entry_id)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert registry.async_get_entity_id("climate", DOMAIN, entry.unique_id) == entity_id
    assert hass.states.get(entity_id).attributes["current_temperature"] == 22
    hass.states.async_set("sensor.inside", "30", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["current_temperature"] == 22


async def test_options_rejects_unsafe_duration(hass, inputs, entry, no_services):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    invalid = {
        **{key: value for key, value in inputs.items() if key != CONF_NAME},
        **Settings().as_dict(),
        "min_on": 0,
        "reset_fault": False,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], invalid
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_setting"}
