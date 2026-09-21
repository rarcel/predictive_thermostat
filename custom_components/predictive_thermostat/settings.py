"""Validated hardware-dependent settings, independent of Home Assistant."""

import math
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class Settings:
    """Temperatures/differences in Celsius, durations in seconds."""

    observation_only: bool = True
    inverted: bool = False
    min_on: float = 1800
    min_off: float = 900
    cooldown: float = 900
    command_timeout: float = 60
    sensor_max_age: float = 7200
    cold_tolerance: float = 0.3
    hot_tolerance: float = 0.3
    min_temperature: float = 5
    max_temperature: float = 30
    target_step: float = 0.5
    initial_target: float = 20
    ignition_delay: float = 10
    heating_rate: float = 0.15
    loss_factor: float = 0.05
    preheat_margin: float = 5
    min_preheat: float = 5
    max_preheat: float = 180

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if item.name in ("observation_only", "inverted"):
                if type(value) is not bool:
                    raise ValueError(item.name)
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(item.name)
        for key in (
            "min_on",
            "min_off",
            "cooldown",
            "command_timeout",
            "sensor_max_age",
            "ignition_delay",
            "preheat_margin",
            "min_preheat",
            "max_preheat",
        ):
            if not 1 <= getattr(self, key) <= 86400:
                raise ValueError(key)
        for key in ("cold_tolerance", "hot_tolerance", "target_step"):
            if not 0 < getattr(self, key) <= 10:
                raise ValueError(key)
        if not 0 < self.heating_rate <= 10 or not 0 <= self.loss_factor <= 10:
            raise ValueError("heating_model")
        if self.min_preheat > self.max_preheat:
            raise ValueError("preheat_range")
        if not -50 <= self.min_temperature < self.max_temperature <= 100:
            raise ValueError("temperature_range")
        if not self.min_temperature <= self.initial_target <= self.max_temperature:
            raise ValueError("initial_target")
        if self.target_step > self.max_temperature - self.min_temperature:
            raise ValueError("target_step")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Settings:
        """Reject unknown settings rather than silently discarding them."""
        return cls(**value)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
