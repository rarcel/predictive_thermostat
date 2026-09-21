"""Validate completed heating cycles without Home Assistant dependencies."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HeatingCycle:
    indoor_start: float
    outdoor_start: float
    target: float
    minutes: float

    def rate(self) -> float | None:
        gain = self.target - self.indoor_start
        if (
            not all(
                math.isfinite(value)
                for value in (
                    self.indoor_start,
                    self.outdoor_start,
                    self.target,
                    self.minutes,
                )
            )
            or gain <= 0
            or not 5 <= self.minutes <= 720
        ):
            return None
        value = gain / self.minutes
        return value if 0.01 <= value <= 2 else None
