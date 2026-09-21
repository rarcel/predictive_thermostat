"""Bounded, explainable preheat estimate without learning or Home Assistant."""

import math
from dataclasses import dataclass

from .settings import Settings


@dataclass(frozen=True)
class Prediction:
    """A conservative duration and why it is available."""

    minutes: float
    confidence: float
    reason: str | None = None


class FallbackModel:
    """Use configured physical assumptions until learning is introduced."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
            + gain / self.settings.heating_rate
            + envelope * self.settings.loss_factor
            + self.settings.preheat_margin
        )
        minutes = min(
            self.settings.max_preheat, max(self.settings.min_preheat, minutes)
        )
        return Prediction(minutes, confidence=0.15, reason="fallback")
