"""Learning accepts only plausible complete cycles and moves slowly."""

from custom_components.predictive_thermostat.model import LearningState
from custom_components.predictive_thermostat.observations import HeatingCycle
from custom_components.predictive_thermostat.settings import Settings


def test_cycle_validation_and_bounded_learning():
    state = LearningState.initial(Settings(heating_rate=0.2))
    invalid = HeatingCycle(20, 5, 19, 20)
    assert state.update(invalid) == state
    updated = state.update(HeatingCycle(17, 5, 20, 30))
    assert updated.samples == 1
    assert updated.heating_rate == 0.19
    assert LearningState.from_dict(updated.as_dict(), Settings()) == updated
    losses = updated.update_losses(HeatingCycle(17, 5, 20, 80), Settings())
    assert losses.loss_factor > updated.loss_factor


def test_arrival_error_is_slow_and_bounded():
    state = LearningState.initial(Settings()).record_arrival_error(120)
    assert state.mean_arrival_error == 6
    for _ in range(100):
        state = state.record_arrival_error(10000)
    assert state.mean_arrival_error <= 60
