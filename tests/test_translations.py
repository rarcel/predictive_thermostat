"""Validate distributable metadata and complete translated forms."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components" / "predictive_thermostat"


def leaf_keys(value, prefix=""):
    return {
        f"{prefix}.{key}" for key, item in value.items() if not isinstance(item, dict)
    } | set().union(
        *(
            leaf_keys(item, f"{prefix}.{key}")
            for key, item in value.items()
            if isinstance(item, dict)
        )
    )


def test_translation_parity():
    english = json.loads((ROOT / "strings.json").read_text())
    for language in ("en", "fr"):
        translated = json.loads(
            (ROOT / "translations" / f"{language}.json").read_text()
        )
        assert leaf_keys(translated) == leaf_keys(english)
        assert translated["config"]["step"]["user"]["description"]


def test_manifest():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert manifest["domain"] == "predictive_thermostat"
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == []
    assert manifest["version"] == "0.4.0"
