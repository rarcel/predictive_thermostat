"""Bounded, explainable preheat estimate without learning or Home Assistant."""

import math
from dataclasses import dataclass

from .observations import HeatingCycle
from .settings import Settings


@dataclass(frozen=True)
class Prediction:
    """A conservative duration and why it is available."""

    minutes: float
    confidence: float
    reason: str | None = None


@dataclass(frozen=True)
class LearningState:
    """Small, private aggregate; no raw timestamps or entity references."""

    heating_rate: float
    loss_factor: float
    samples: int = 0
    mean_arrival_error: float = 0.0

    @classmethod
    def initial(cls, settings: Settings) -> LearningState:
        return cls(settings.heating_rate, settings.loss_factor)

    def update(self, cycle: HeatingCycle) -> LearningState:
        rate = cycle.rate()
        if rate is None:
            return self
        alpha = min(0.1, 1 / (self.samples + 1))
        updated = min(
            2.0, max(0.01, self.heating_rate + alpha * (rate - self.heating_rate))
        )
        return LearningState(
            updated, self.loss_factor, self.samples + 1, self.mean_arrival_error
        )

    def update_losses(self, cycle: HeatingCycle, settings: Settings) -> LearningState:
        """Estimate plausible outdoor loss slowly, without retaining raw cycles."""
        if cycle.rate() is None:
            return self
        envelope = max(0.0, cycle.indoor_start - cycle.outdoor_start)
        if envelope < 1:
            return self
        gain = cycle.target - cycle.indoor_start
        candidate = (
            cycle.minutes
            - settings.ignition_delay
            - gain / self.heating_rate
            - settings.preheat_margin
        ) / envelope
        if not math.isfinite(candidate) or not 0 <= candidate <= 10:
            return self
        loss = min(
            10.0, max(0.0, self.loss_factor + 0.05 * (candidate - self.loss_factor))
        )
        return LearningState(
            self.heating_rate, loss, self.samples, self.mean_arrival_error
        )

    def record_arrival_error(self, minutes: float) -> LearningState:
        """Correct the estimate slowly; an outlier cannot dominate the model."""
        if not math.isfinite(minutes):
            return self
        bounded = max(-120.0, min(120.0, minutes))
        return LearningState(
            self.heating_rate,
            self.loss_factor,
            self.samples,
            max(
                -60.0,
                min(
                    60.0,
                    self.mean_arrival_error
                    + 0.05 * (bounded - self.mean_arrival_error),
                ),
            ),
        )

    def as_dict(self) -> dict[str, float | int]:
        return {
            "heating_rate": self.heating_rate,
            "loss_factor": self.loss_factor,
            "samples": self.samples,
            "mean_arrival_error": self.mean_arrival_error,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object], settings: Settings) -> LearningState:
        try:
            rate_value = value["heating_rate"]
            loss_value = value.get("loss_factor", settings.loss_factor)
            samples = value["samples"]
            error_value = value.get("mean_arrival_error", 0.0)
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("learning_state") from err
        if (
            isinstance(rate_value, bool)
            or not isinstance(rate_value, (int, float, str))
            or isinstance(error_value, bool)
            or not isinstance(error_value, (int, float, str))
            or isinstance(loss_value, bool)
            or not isinstance(loss_value, (int, float, str))
        ):
            raise ValueError("learning_state")
        try:
            rate = float(rate_value)
            error = float(error_value)
            loss = float(loss_value)
        except ValueError as err:
            raise ValueError("learning_state") from err
        if (
            not math.isfinite(rate)
            or not math.isfinite(error)
            or not math.isfinite(loss)
            or type(samples) is not int
            or not 0 <= samples <= 100000
        ):
            raise ValueError("learning_state")
        return cls(
            min(2.0, max(0.01, rate)),
            min(10.0, max(0.0, loss)),
            samples,
            max(-240.0, min(240.0, error)),
        )


class FallbackModel:
    """Use configured physical assumptions until learning is introduced."""

    def __init__(
        self, settings: Settings, learning: LearningState | None = None
    ) -> None:
        self.settings = settings
        self.learning = learning or LearningState.initial(settings)

    def predict(
        self, indoor: float | None, outdoor: float | None, target: float
    ) -> Prediction | None:
        """Return a bounded estimate; absent exterior disables early heating."""
        if (
            indoor is None
            or outdoor is None
            or not all(math.isfinite(value) for value in (indoor, outdoor, target))
            or not self.settings.min_temperature
            <= target
            <= self.settings.max_temperature
        ):
            return None
        gain = max(0.0, target - indoor)
        envelope = max(0.0, indoor - outdoor)
        minutes = (
            self.settings.ignition_delay
            + gain / self.learning.heating_rate
            + envelope * self.learning.loss_factor
            + self.settings.preheat_margin
            + self.learning.mean_arrival_error
        )
        minutes = min(
            self.settings.max_preheat, max(self.settings.min_preheat, minutes)
        )
        confidence = min(0.9, 0.15 + self.learning.samples / 100)
        return Prediction(
            minutes,
            confidence=confidence,
            reason="learned" if self.learning.samples else "fallback",
        )
