"""Serve the Lovelace card bundled with the integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.const import CONF_RESOURCE_TYPE_WS
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import CONF_ID, CONF_URL
from homeassistant.core import HomeAssistant

CARD_VERSION = "0.7.7"
CARD_URL = (
    f"/predictive_thermostat/predictive-thermostat-card-{CARD_VERSION}.js"
)
CARD_PATH = Path(__file__).parent / "frontend" / "predictive-thermostat-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the card and register it before Lovelace builds custom cards."""
    await hass.http.async_register_static_paths(
        # The versioned path invalidates reverse-proxy caches which ignore query
        # parameters. Disabling browser cache headers also prevents a proxy from
        # retaining the module longer than the integration version.
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or lovelace.resource_mode != MODE_STORAGE:
        # YAML resource mode cannot be mutated; retain the non-persistent
        # frontend fallback for those installations.
        add_extra_js_url(hass, CARD_URL)
        return

    resources = cast(ResourceStorageCollection, lovelace.resources)
    await resources.async_get_info()
    owned: list[dict[str, Any]] = [
        item
        for item in resources.async_items()
        if str(item.get(CONF_URL, "")).startswith("/predictive_thermostat/")
    ]
    if owned:
        primary = owned[0]
        if primary.get(CONF_URL) != CARD_URL or primary.get("type") != "module":
            await resources.async_update_item(
                primary[CONF_ID],
                {CONF_URL: CARD_URL, CONF_RESOURCE_TYPE_WS: "module"},
            )
        for duplicate in owned[1:]:
            await resources.async_delete_item(duplicate[CONF_ID])
        return
    await resources.async_create_item(
        {CONF_URL: CARD_URL, CONF_RESOURCE_TYPE_WS: "module"}
    )
