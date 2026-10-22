"""Serve the Lovelace card bundled with the integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

CARD_URL = "/predictive_thermostat/predictive-thermostat-card.js"
CARD_VERSION = "0.6.2"
CARD_PATH = Path(__file__).parent / "frontend" / "predictive-thermostat-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose and load the card once during integration setup."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={CARD_VERSION}")
