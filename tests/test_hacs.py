"""Distribution metadata stays deliberately free of invented repository URLs."""

import json
from pathlib import Path


def test_hacs_metadata():
    metadata = json.loads((Path(__file__).parents[1] / "hacs.json").read_text())
    assert metadata == {
        "name": "Predictive Thermostat",
        "render_readme": True,
        "homeassistant": "2026.9.3",
    }
