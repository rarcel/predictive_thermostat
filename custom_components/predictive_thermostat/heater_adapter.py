"""Switch transport only; every decision belongs to CycleController."""

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .sources import resolve


class SwitchAdapter:
    """A maintained contact, with configurable logical inversion."""

    def __init__(
        self, hass: HomeAssistant, source: dict[str, str], inverted: bool
    ) -> None:
        self.hass = hass
        self.source = source
        self.inverted = inverted

    def observed(self) -> bool | None:
        entity_id = resolve(self.hass, self.source)
        state = self.hass.states.get(entity_id) if entity_id else None
        if (
            state is None
            or state.attributes.get("restored")
            or state.state not in (STATE_ON, STATE_OFF)
        ):
            return None
        return (state.state == STATE_ON) != self.inverted

    async def command(self, on: bool) -> None:
        """Validate again immediately before sending to the selected entity only."""
        entity_id = resolve(self.hass, self.source)
        service = "turn_on" if on != self.inverted else "turn_off"
        if (
            entity_id is None
            or self.observed() is None
            or not self.hass.services.has_service("switch", service)
        ):
            raise HomeAssistantError("Heater service or state unavailable")
        await self.hass.services.async_call(
            "switch", service, {"entity_id": entity_id}, blocking=True
        )
