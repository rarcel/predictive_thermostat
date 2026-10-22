"""End-to-end simulated switch control, entirely inside the HA test harness."""

from datetime import datetime
from unittest.mock import patch
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
        entry,
        options={
            "settings": Settings(
                observation_only=False, command_timeout=1
            ).as_dict()
        },
    )
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("switch", "turn_on", record)
    entity_id, thermostat = await _entity(hass, entry)
    hass.states.async_set("switch.heater", "unavailable")
    await hass.async_block_till_done()
    assert thermostat.runtime.core.fault is None
    assert not hass.states.get(entity_id).attributes["heater_available"]
    assert hass.states.get(entity_id).attributes["control_state"] == "reconciling"
    assert thermostat.runtime._actuator_unavailable_since is not None
    thermostat.runtime._actuator_unavailable_since -= 2
    with patch(
        "custom_components.predictive_thermostat.runtime."
        "persistent_notification.async_create"
    ) as create:
        thermostat.runtime.request()
        await hass.async_block_till_done()
    create.assert_called_once()
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


async def test_transient_actuator_unavailability_recovers_without_fault(hass, entry):
    entity_id, thermostat = await _entity(hass, entry)

    hass.states.async_set("switch.heater", "unavailable")
    await hass.async_block_till_done()
    assert thermostat.runtime.core.fault is None
    assert thermostat.runtime.decision.state == "reconciling"
    assert hass.states.get(entity_id).attributes["control_state"] == "observation"

    hass.states.async_set("switch.heater", "off")
    await hass.async_block_till_done()
    assert thermostat.runtime.core.fault is None
    assert hass.states.get(entity_id).attributes["heater_available"]


async def test_confirmed_actuator_recovery_clears_availability_fault(hass, entry):
    hass.config_entries.async_update_entry(
        entry,
        options={
            "settings": Settings(command_timeout=1).as_dict(),
        },
    )
    entity_id, thermostat = await _entity(hass, entry)
    hass.states.async_set("switch.heater", "unavailable")
    await hass.async_block_till_done()
    assert thermostat.runtime._actuator_unavailable_since is not None
    thermostat.runtime._actuator_unavailable_since -= 2
    thermostat.runtime.request()
    await hass.async_block_till_done()
    assert thermostat.runtime.core.fault == "actuator_unavailable"

    hass.states.async_set("switch.heater", "off")
    await hass.async_block_till_done()
    assert thermostat.runtime.core.fault is None
    assert hass.states.get(entity_id).attributes["control_state"] == "observation"


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


async def test_restart_preserves_confirmed_heating_without_command(hass, entry):
    """A HA restart must leave a confirmed maintained contact heating."""
    hass.config_entries.async_update_entry(
        entry,
        options={
            "settings": Settings(
                observation_only=False,
                min_on=600,
                min_off=60,
                cooldown=60,
            ).as_dict()
        },
    )
    calls = []

    async def record(call):
        calls.append(call.service)

    hass.services.async_register("switch", "turn_on", record)
    hass.services.async_register("switch", "turn_off", record)
    hass.states.async_set("switch.heater", "on")

    entity_id, thermostat = await _entity(hass, entry)
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": entity_id, "temperature": 22, "hvac_mode": "heat"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert thermostat.runtime.core.observed is True
    assert hass.states.get(entity_id).attributes["hvac_action"] == "heating"
    assert not calls

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("switch.heater").state == "on"
    assert not calls

    restored_id, restored = await _entity(hass, entry)
    assert restored_id == entity_id
    assert restored.runtime.mode == "heat"
    assert restored.runtime.target == 22
    assert restored.runtime.core.observed is True
    state = hass.states.get(restored_id)
    assert state.state == "heat"
    assert state.attributes["hvac_action"] == "heating"
    assert state.attributes["control_state"] == "heating"
    assert hass.states.get("switch.heater").state == "on"
    assert not calls


async def test_registry_resubscribe_survives_a_consumed_listener(hass, entry):
    """A registry update must not make the climate entity fail to reload."""
    _, thermostat = await _entity(hass, entry)
    consumed = thermostat.runtime._source_listeners[0]
    consumed()

    thermostat.runtime._subscribe()

    assert len(thermostat.runtime._source_listeners) == 2


async def test_learning_stops_when_target_is_first_reached(hass, entry):
    _, thermostat = await _entity(hass, entry)
    runtime = thermostat.runtime
    runtime.target = 21
    runtime.indoor = 18
    runtime.outdoor = 5
    runtime.core.observe(True)
    runtime._learn_cycle()
    assert runtime._cycle_started is not None

    started, indoor, outdoor, target = runtime._cycle_started
    runtime._cycle_started = (started - 600, indoor, outdoor, target)
    runtime.indoor = 21
    runtime._learn_cycle()

    assert runtime.learning.samples == 1
    assert runtime._cycle_reached_target
    assert runtime._cycle_started is None

    runtime.indoor = 22
    runtime._learn_cycle()
    assert runtime.learning.samples == 1


async def test_learning_ignores_heating_started_at_or_above_target(hass, entry):
    _, thermostat = await _entity(hass, entry)
    runtime = thermostat.runtime
    runtime.target = 20
    runtime.indoor = 20
    runtime.outdoor = 5
    runtime.core.observe(True)

    runtime._learn_cycle()

    assert runtime._cycle_started is None
    assert runtime.learning.samples == 0


async def test_late_schedule_arrival_updates_prediction_correction(hass, entry):
    """Reaching the target after its scheduled time must still be learned."""
    _, thermostat = await _entity(hass, entry)
    runtime = thermostat.runtime
    target_at = datetime(2026, 9, 21, 7, 15, tzinfo=ZoneInfo("Europe/Paris"))
    runtime._arrival_expected = (
        target_at,
        20.5,
        datetime(2026, 9, 21, 6, 50, tzinfo=ZoneInfo("Europe/Paris")),
    )
    runtime.indoor = 20.5

    runtime._record_arrival(
        datetime(2026, 9, 21, 7, 34, tzinfo=ZoneInfo("Europe/Paris"))
    )

    assert abs(runtime.learning.mean_arrival_error - 0.95) < 1e-9
    assert runtime._arrival_recorded_for == target_at
    assert runtime._arrival_expected is None
    saved = runtime._snapshot()
    assert saved["arrival_recorded_for"] == target_at.isoformat()


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
    assert state.attributes["prediction_outdoor_temperature"] == 8
    assert state.attributes["prediction_outdoor_source"] == "sensor"
    assert state.attributes["prediction_temperature_gain_minutes"] > 0
    assert state.attributes["prediction_outdoor_loss_minutes"] > 0
    assert state.attributes["learned_heating_rate"] > 0


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
