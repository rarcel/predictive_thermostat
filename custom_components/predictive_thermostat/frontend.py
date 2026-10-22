"""Serve the Lovelace card bundled with the integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

CARD_VERSION = "0.7.2"
CARD_URL = (
    f"/predictive_thermostat/predictive-thermostat-card-{CARD_VERSION}.js"
)
CARD_PATH = Path(__file__).parent / "frontend" / "predictive-thermostat-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose and load the card once during integration setup."""
    await hass.http.async_register_static_paths(
        # The versioned path invalidates reverse-proxy caches which ignore query
        # parameters. Disabling browser cache headers also prevents a proxy from
        # retaining the module longer than the integration version.
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    add_extra_js_url(hass, CARD_URL)
