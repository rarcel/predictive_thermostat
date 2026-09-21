"""The switch transport validates state/service immediately before an order."""

from dataclasses import dataclass

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.predictive_thermostat.heater_adapter import SwitchAdapter


@dataclass
class State:
    state: str
    attributes: dict


class States:
    def __init__(self, state):
        self.value = state

    def get(self, entity_id):
        return self.value


class Services:
    def __init__(self):
        self.calls = []
        self.available = True

    def has_service(self, domain, service):
        return self.available

    async def async_call(self, domain, service, data, blocking):
        self.calls.append((domain, service, data, blocking))


class Hass:
    def __init__(self, state):
        self.states = States(state)
        self.services = Services()


@pytest.mark.parametrize(
    ("inverted", "logical_on", "expected"),
    [
        (False, True, "turn_on"),
        (False, False, "turn_off"),
        (True, True, "turn_off"),
        (True, False, "turn_on"),
    ],
)
async def test_commands_selected_switch_with_polarity(inverted, logical_on, expected):
    hass = Hass(State("off", {}))
    adapter = SwitchAdapter(hass, {"entity_id": "switch.test"}, inverted)
    await adapter.command(logical_on)
    assert hass.services.calls == [
        ("switch", expected, {"entity_id": "switch.test"}, True)
    ]


@pytest.mark.parametrize(
    "state", [None, State("unavailable", {}), State("on", {"restored": True})]
)
async def test_invalid_switch_never_calls_service(state):
    hass = Hass(state)
    adapter = SwitchAdapter(hass, {"entity_id": "switch.test"}, False)
    with pytest.raises(HomeAssistantError):
        await adapter.command(True)
    assert not hass.services.calls


async def test_missing_service_never_calls():
    hass = Hass(State("off", {}))
    hass.services.available = False
    adapter = SwitchAdapter(hass, {"entity_id": "switch.test"}, False)
    with pytest.raises(HomeAssistantError):
        await adapter.command(True)
    assert not hass.services.calls
