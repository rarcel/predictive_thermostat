"""The fallback is explainable, bounded and does not learn from test input."""

from dataclasses import replace

from custom_components.predictive_thermostat.model import FallbackModel
from custom_components.predictive_thermostat.settings import Settings


def test_fallback_is_bounded_and_uses_outdoor_temperature():
    settings = Settings(
        ignition_delay=5,
        heating_rate=0.5,
        loss_factor=0.5,
        preheat_margin=2,
        min_preheat=1,
        max_preheat=90,
    )
    model = FallbackModel(settings)
    mild = model.predict(17, 12, 20)
    cold = model.predict(17, -5, 20)
    assert mild is not None and cold is not None
    assert mild.minutes == 15.5
    assert mild.ignition_minutes == 5
    assert mild.temperature_gain_minutes == 6
    assert mild.outdoor_loss_minutes == 2.5
    assert mild.margin_minutes == 2
    assert mild.unbounded_minutes == mild.minutes
    assert cold.minutes > mild.minutes
    assert cold.confidence == 0.15
    assert model.predict(None, 5, 20) is None
    assert model.predict(17, None, 20) is None
    assert (
        FallbackModel(replace(settings, max_preheat=10)).predict(0, -50, 30).minutes
        == 10
    )


def test_fallback_increases_with_target_gain():
    model = FallbackModel(Settings())
    low = model.predict(18, 5, 19)
    high = model.predict(18, 5, 22)
    assert low is not None and high is not None
    assert high.minutes > low.minutes


def test_fallback_is_zero_when_target_is_already_reached():
    model = FallbackModel(Settings(min_preheat=10))

    at_target = model.predict(20, 5, 20)
    above_target = model.predict(21, 5, 20)

    assert at_target is not None and at_target.minutes == 0
    assert above_target is not None and above_target.minutes == 0
