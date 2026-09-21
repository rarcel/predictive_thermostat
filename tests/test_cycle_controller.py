"""Pure state-machine tests; time advances without sleep or Home Assistant."""

from dataclasses import replace
import random

import pytest

from custom_components.predictive_thermostat.cycle_controller import CycleController
from custom_components.predictive_thermostat.settings import Settings


class Clock:
    now = 0.0
    def __call__(self):
        return self.now


@pytest.fixture
def controller():
    clock = Clock()
    return CycleController(Settings(min_on=30, min_off=20, cooldown=40, command_timeout=10), clock), clock


def test_reconcile_cooldown_pending_confirmation(controller):
    core, clock = controller
    assert core.decide(True, 20, 17).command is None
    core.observe(False)
    assert core.decide(True, 20, 17).deadline == 40
    clock.now = 40
    assert core.decide(True, 20, 17).command is True
    core.start_command(True)
    for _ in range(100):
        assert core.decide(True, 20, 17).command is None
    clock.now = 45
    core.observe(True)
    assert core.pending is None
    assert core.decide(False, 20, 25).deadline == 75
    clock.now = 75
    assert core.decide(False, 20, 25).command is False


def test_off_and_invalid_sensor_respect_runtime(controller):
    core, clock = controller
    core.observe(True)
    for temp in (None, float("nan"), float("inf")):
        assert core.decide(True, 20, temp).state == "minimum_runtime"
    clock.now = 30
    assert core.decide(True, 20, None).command is False


def test_timeout_is_sticky_even_with_late_confirmation(controller):
    core, clock = controller
    core.observe(False)
    clock.now = 40
    core.start_command(True)
    clock.now = 50
    core.observe(True)
    assert core.fault == "command_timeout"
    for heat in (False, True):
        assert core.decide(heat, 20, 10).state == "fault"
        assert core.decide(heat, 20, 10).command is None


def test_restart_reapplies_full_protection(controller):
    core, clock = controller
    clock.now = 1000
    core.observe(True)
    assert core.decide(False, 20, 21).deadline == 1030


def test_external_transition_and_disconnection(controller):
    core, clock = controller
    core.observe(True)
    clock.now = 60
    core.observe(False)
    assert core.decide(True, 20, 15).deadline == 100
    core.observe(None)
    core.observe(False)
    assert core.fault == "actuator_unavailable"
    assert core.decide(True, 20, 15).command is None


def test_hysteresis(controller):
    core, clock = controller
    core.observe(False)
    clock.now = 100
    assert core.decide(True, 20, 19.8).command is None
    assert core.decide(True, 20, 19.7).command is True
    core.observe(True)
    clock.now = 200
    assert core.decide(True, 20, 20.2).command is None
    assert core.decide(True, 20, 20.3).command is False


def test_randomized_cycle_invariants(controller):
    core, clock = controller
    core.observe(False)
    randomizer = random.Random(42)
    commands = []
    for _ in range(3000):
        clock.now += randomizer.random() * 3
        decision = core.decide(randomizer.choice([True, True, False]), 20, randomizer.choice([15, 19.9, 25, None]))
        if decision.command is not None:
            duration = core.settings.min_on if core.observed else max(core.settings.min_off, core.settings.cooldown)
            assert clock.now - core.since >= duration
            core.start_command(decision.command)
            assert core.decide(True, 20, 15).command is None
            commands.append(decision.command)
            core.observe(decision.command)
    assert len(commands) > 20
    assert all(a != b for a, b in zip(commands, commands[1:]))


@pytest.mark.parametrize("field,value", [("min_on", 0), ("cooldown", -1), ("cold_tolerance", float("nan")), ("command_timeout", float("inf")), ("inverted", "yes"), ("initial_target", 99), ("target_step", 0)])
def test_invalid_settings(field, value):
    with pytest.raises(ValueError):
        replace(Settings(), **{field: value})
