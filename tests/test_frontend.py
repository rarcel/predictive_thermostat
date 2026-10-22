"""Tests for the bundled Lovelace card and its registration."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.predictive_thermostat.frontend import (
    CARD_PATH,
    CARD_URL,
    CARD_VERSION,
    async_register_card,
)


async def test_register_card():
    register = AsyncMock()
    hass = MagicMock()
    hass.http = SimpleNamespace(async_register_static_paths=register)
    with patch(
        "custom_components.predictive_thermostat.frontend.add_extra_js_url"
    ) as add_url:
        await async_register_card(hass)

    static_paths = register.call_args.args[0]
    assert len(static_paths) == 1
    assert static_paths[0].url_path == CARD_URL
    assert Path(static_paths[0].path) == CARD_PATH
    assert static_paths[0].cache_headers is True
    add_url.assert_called_once_with(hass, f"{CARD_URL}?v={CARD_VERSION}")


def test_card_contains_actions_and_predictive_details():
    source = CARD_PATH.read_text(encoding="utf-8")
    assert "customElements.define(CARD_TYPE, PredictiveThermostatCard)" in source
    assert '"predictive_thermostat", "reset_fault"' in source
    assert "confirmed_off_period: confirmedOffPeriod" in source
    assert "predicted_start_time" in source
    assert "prediction_confidence" in source
    assert 'addEventListener("hass-more-info"' in source
    assert 'new CustomEvent("hass-more-info"' in source
    assert 'class="menu-button"' not in source
