"""Single authority for heater transitions; no Home Assistant dependency or I/O."""

import math
from collections.abc import Callable
from dataclasses import dataclass

from .settings import Settings


@dataclass(frozen=True)
class Decision:
    state: str
    command: bool | None = None
    deadline: float | None = None


class CycleController:
    """Use an injected monotonic clock and explicitly confirmed relay states."""

    def __init__(self, settings: Settings, clock: Callable[[], float]) -> None:
        self.settings = settings
        self.clock = clock
        self.observed: bool | None = None
        self.since: float | None = None
        self.pending: bool | None = None
        self.pending_until: float | None = None
        self.fault: str | None = None

    def fail(self, reason: str) -> None:
        """Latch the first fault; modes and subsequent states cannot clear it."""
        if self.fault is None:
            self.fault = reason

    def observe(self, value: bool | None) -> None:
        """Record all transitions, including external changes while awaiting I/O."""
        now = self.clock()
        if self.pending_until is not None and now >= self.pending_until:
            self.fail("command_timeout")
        if value is None:
            if self.since is not None or self.pending is not None:
                self.fail("actuator_unavailable")
            self.observed = None
            self.since = None
            return
        if self.observed is None or value != self.observed:
            self.since = now
        self.observed = value
        if self.pending is not None and value == self.pending and self.fault is None:
            self.pending = None
            self.pending_until = None

    def recover_actuator_unavailable(self) -> bool:
        """Clear only an availability fault after a confirmed source recovery."""
        if (
            self.fault == "actuator_unavailable"
            and self.pending is None
            and self.observed is not None
        ):
            self.fault = None
            return True
        return False

    def acknowledge_fault(self, *, confirmed_off_period: bool = False) -> bool:
        """Clear a latched fault only after a safe actuator reconciliation."""
        had_fault = self.fault is not None
        if not had_fault and not confirmed_off_period:
            return True
        if self.observed is None:
            return False
        if confirmed_off_period and self.observed:
            return False
        if not had_fault and self.pending is not None:
            return False
        # Explicit acknowledgement accepts the currently confirmed actuator
        # state as authoritative, even when a previous command expected the
        # opposite state. Full cycle protection restarts below before another
        # command can be emitted.
        if had_fault:
            self.pending = None
        self.fault = None
        self.pending_until = None
        now = self.clock()
        self.since = (
            now - max(self.settings.min_off, self.settings.cooldown)
            if confirmed_off_period
            else now
        )
        return True

    def decide(self, heat: bool, target: float, temperature: float | None) -> Decision:
        """Return an intent; only start_command reserves an actual command."""
        now = self.clock()
        if self.pending_until is not None and now >= self.pending_until:
            self.fail("command_timeout")
        if self.fault is not None:
            return Decision("fault")
        if self.observed is None or self.since is None:
            return Decision("reconciling")
        if self.pending is not None:
            return Decision(
                "actuator_starting" if self.pending else "actuator_stopping",
                deadline=self.pending_until,
            )
        valid = (
            temperature is not None
            and math.isfinite(temperature)
            and math.isfinite(target)
        )
        if not self.settings.min_temperature <= target <= self.settings.max_temperature:
            valid = False
        desired = self.observed
        if not heat or not valid:
            desired = False
        elif temperature is not None:
            if self.observed and temperature >= target + self.settings.hot_tolerance:
                desired = False
            elif (
                not self.observed
                and temperature <= target - self.settings.cold_tolerance
            ):
                desired = True
        protection = (
            self.settings.min_on
            if self.observed
            else max(self.settings.min_off, self.settings.cooldown)
        )
        until = self.since + protection
        if desired != self.observed:
            if now < until:
                return Decision(
                    "minimum_runtime" if self.observed else "cooldown", deadline=until
                )
            return Decision(
                "actuator_starting" if desired else "actuator_stopping", command=desired
            )
        return Decision("heating" if self.observed else "idle" if heat else "off")

    def start_command(self, on: bool) -> None:
        """Reserve before any await, so repeated decisions cannot duplicate an order."""
        if self.fault or self.pending is not None or self.observed is None:
            raise RuntimeError("Command not permitted")
        self.pending = on
        self.pending_until = self.clock() + self.settings.command_timeout
