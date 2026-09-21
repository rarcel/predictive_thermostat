"""Fixtures contain no real installation identifiers or network credentials."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.predictive_thermostat.const import (
    CONF_HEATER,
    CONF_INDOOR,
    CONF_OUTDOOR,
    DOMAIN,
)
from custom_components.predictive_thermostat.sources import reference


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Enable only the local test integration."""


@pytest.fixture
def inputs(hass: HomeAssistant) -> dict[str, str]:
    registry = er.async_get(hass)
    for name in ("inside", "outside"):
        registry.async_get_or_create(
            "sensor",
            "test",
            name,
            suggested_object_id=name,
            original_device_class="temperature",
        )
        hass.states.async_set(
            f"sensor.{name}",
            "20" if name == "inside" else "8",
            {"device_class": "temperature", "unit_of_measurement": "°C"},
        )
    registry.async_get_or_create(
        "switch", "test", "heater", suggested_object_id="heater"
    )
    hass.states.async_set("switch.heater", "off")
    return {
        CONF_NAME: "Test zone",
        CONF_INDOOR: "sensor.inside",
        CONF_OUTDOOR: "sensor.outside",
        CONF_HEATER: "switch.heater",
    }


@pytest.fixture
def entry(hass: HomeAssistant, inputs: dict[str, str]) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=inputs[CONF_NAME],
        unique_id="stable-zone-uuid",
        data={
            key: reference(hass, value)
            for key, value in inputs.items()
            if key != CONF_NAME
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def no_services(hass: HomeAssistant) -> Generator[AsyncMock]:
    """Catch every service invocation, including accidental OFF during unload."""
    with patch.object(
        type(hass.services), "async_call", new_callable=AsyncMock
    ) as mock:
        yield mock
        mock.assert_not_called()
