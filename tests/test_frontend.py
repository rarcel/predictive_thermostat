"""Tests for the bundled Lovelace card and its registration."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE

from custom_components.predictive_thermostat.frontend import (
    CARD_PATH,
    CARD_URL,
    CARD_VERSION,
    async_register_card,
)


async def test_register_card():
    register = AsyncMock()
    resources = SimpleNamespace(
        async_get_info=AsyncMock(),
        async_items=MagicMock(return_value=[]),
        async_create_item=AsyncMock(),
        async_update_item=AsyncMock(),
        async_delete_item=AsyncMock(),
    )
    hass = MagicMock()
    hass.http = SimpleNamespace(async_register_static_paths=register)
    hass.data = {
        LOVELACE_DATA: SimpleNamespace(
            resource_mode=MODE_STORAGE, resources=resources
        )
    }
    with patch(
        "custom_components.predictive_thermostat.frontend.add_extra_js_url"
    ) as add_url:
        await async_register_card(hass)

    static_paths = register.call_args.args[0]
    assert len(static_paths) == 1
    assert static_paths[0].url_path == CARD_URL
    assert Path(static_paths[0].path) == CARD_PATH
    assert static_paths[0].cache_headers is False
    assert CARD_VERSION in CARD_URL
    add_url.assert_not_called()
    resources.async_get_info.assert_awaited_once()
    resources.async_create_item.assert_awaited_once_with(
        {"url": CARD_URL, "res_type": "module"}
    )


def test_card_contains_actions_and_predictive_details():
    source = CARD_PATH.read_text(encoding="utf-8")
    assert "customElements.define(CARD_TYPE, PredictiveThermostatCard)" in source
    assert '"predictive_thermostat", "reset_fault"' in source
    assert "confirmed_off_period: confirmedOffPeriod" in source
    assert "predicted_start_time" in source
    assert "prediction_confidence" in source
    assert 'customElements.define("predictive-details-card-feature"' in source
    assert 'type: "custom:predictive-details-card-feature"' in source
    assert 'new CustomEvent("predictive-thermostat-show-details"' in source
    assert 'class="details-trigger"' not in source
    assert 'addEventListener("hass-more-info"' not in source
    assert 'class="menu-button"' not in source
    assert "if (!this._config || !this._hass || this._nativeCard) return" in source
    assert "this._nativeCardPromise" in source
    assert "nativeCard.hass = this._hass" in source
    assert "this._hass.states?.[this._config.entity]" in source
    assert 'customElements.whenDefined("hui-thermostat-card")' in source
    assert 'document.createElement("hui-thermostat-card")' in source
    assert "nativeCard.setConfig(cardConfig)" in source
    assert "helpers.createCardElement" not in source
