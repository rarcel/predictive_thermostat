"""End-to-end simulated switch control, entirely inside the HA test harness."""

from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.helpers import entity_component
from homeassistant.helpers import entity_registry as er

from custom_components.predictive_thermostat.const import DOMAIN
from custom_components.predictive_thermostat.schedule import WeekSchedule
from custom_components.predictive_thermostat.settings import Settings


async def _entity(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "climate", DOMAIN, entry.unique_id
    )
    component = hass.data[entity_component.DATA_INSTANCES]["climate"]
    return entity_id, component.get_entity(entity_id)


async def test_hardware_mode_uses_one_confirmed_switch_command(hass, entry):
    hass.config_entries.async_update_entry(
        entry,
        options={
            "settings": Settings(
                observation_only=False,
                min_on=1,
                min_off=1,
                cooldown=1,
                command_timeout=30,
                cold_tolerance=0.1,
                hot_tolerance=0.1,
            ).as_dict()
        },
    )
    calls = []

    async def turn_on(on):
        calls.append("on")
        hass.states.async_set("switch.heater", "on")

    async def turn_off(on):
        calls.append("off")
        hass.states.async_set("switch.heater", "off")

    entity_id, thermostat = await _entity(hass, entry)
    thermostat.runtime.adapter.command = turn_on
    thermostat.runtime.core.since -= 2
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": entity_id, "temperature": 22, "hvac_mode": "heat"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert calls == ["on"]
    assert hass.states.get("switch.heater").state == "on"
    assert hass.states.get(entity_id).attributes["control_state"] == "heating"
    thermostat.runtime.core.since -= 2
    thermostat.runtime.adapter.command = turn_off
    hass.states.async_set("sensor.inside", "23", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    assert calls == ["on", "off"]


async def test_observation_never_calls_registered_switch_service(hass, entry):
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("switch", "turn_on", record)
    hass.services.async_register("switch", "turn_off", record)
    entity_id, thermostat = await _entity(hass, entry)
    thermostat.runtime.core.since -= 99999
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": entity_id, "temperature": 22, "hvac_mode": "heat"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert not calls
    assert hass.states.get("switch.heater").state == "off"
    assert hass.states.get(entity_id).attributes["control_state"] == "observation"


async def test_actuator_unavailable_latches_fault_without_service(hass, entry):
    hass.config_entries.async_update_entry(
        entry, options={"settings": Settings(observation_only=False).as_dict()}
    )
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("switch", "turn_on", record)
    entity_id, thermostat = await _entity(hass, entry)
    hass.states.async_set("switch.heater", "unavailable")
    await hass.async_block_till_done()
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "heat"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert thermostat.runtime.core.fault == "actuator_unavailable"
    assert hass.states.get(entity_id).attributes["control_state"] == "fault"
    assert not calls


async def test_unload_never_commands_the_switch(hass, entry):
    hass.config_entries.async_update_entry(
        entry, options={"settings": Settings(observation_only=False).as_dict()}
    )
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("switch", "turn_on", record)
    hass.services.async_register("switch", "turn_off", record)
    _, thermostat = await _entity(hass, entry)
    thermostat.runtime.core.observe(True)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not calls


async def test_auto_uses_schedule_then_manual_override(hass, entry):
    schedule = WeekSchedule.default(17)
    hass.config_entries.async_update_entry(
        entry,
        options={"settings": Settings().as_dict(), "schedule": schedule.as_dict()},
    )
    entity_id, _ = await _entity(hass, entry)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": "auto"}, True
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "auto"
    assert state.attributes["temperature"] == 17
    assert state.attributes["next_target_temperature"] == 17
    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": entity_id, "temperature": 22}, True
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes["temperature"] == 22
    assert state.attributes["override_until"] is not None


async def test_auto_starts_only_inside_bounded_preheat_window(hass, entry):
    fields = WeekSchedule.default(17).fields()
    fields["monday"] = "00:00=17, 11:00=22"
    schedule = WeekSchedule.from_fields(fields)
    hass.config_entries.async_update_entry(
        entry,
        options={"settings": Settings().as_dict(), "schedule": schedule.as_dict()},
    )
    entity_id, thermostat = await _entity(hass, entry)
    now = datetime(2026, 9, 21, 10, 0, tzinfo=ZoneInfo("Europe/Paris"))
    thermostat.runtime._local_now = lambda: now
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": "auto"}, True
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes["temperature"] == 17
    assert state.attributes["predicted_start_time"] is not None
    now = now.replace(hour=10, minute=45)
    hass.states.async_set("sensor.inside", "20", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes["temperature"] == 22
    assert state.attributes["predicted_heating_minutes"] is not None


async def test_auto_without_outdoor_temperature_does_not_preheat(hass, entry):
    fields = WeekSchedule.default(17).fields()
    fields["monday"] = "00:00=17, 11:00=22"
    hass.config_entries.async_update_entry(
        entry,
        options={
            "settings": Settings().as_dict(),
            "schedule": WeekSchedule.from_fields(fields).as_dict(),
        },
    )
    entity_id, thermostat = await _entity(hass, entry)
    thermostat.runtime._local_now = lambda: datetime(
        2026, 9, 21, 10, 45, tzinfo=ZoneInfo("Europe/Paris")
    )
    hass.states.async_set("sensor.outside", "unavailable")
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": "auto"}, True
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes["temperature"] == 17
    assert state.attributes["predicted_start_time"] is None
    assert state.attributes["prediction_reason"] == "outdoor_unavailable"
