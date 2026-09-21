"""Validate a short, local forecast before it can influence estimation."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ForecastTemperature:
    when: datetime
    temperature: float


def temperature_at(
    forecast: list[dict[str, Any]], target: datetime, fallback: float | None
) -> float | None:
    """Return nearest valid forecast within three hours, otherwise local fallback."""
    candidates: list[ForecastTemperature] = []
    for item in forecast:
        try:
            when = datetime.fromisoformat(item["datetime"])
            value = float(item["temperature"])
        except KeyError, TypeError, ValueError:
            continue
        if when.tzinfo is not None and math.isfinite(value):
            candidates.append(ForecastTemperature(when, value))
    if not candidates:
        return fallback
    nearest = min(
        candidates, key=lambda point: abs((point.when - target).total_seconds())
    )
    return (
        nearest.temperature
        if abs((nearest.when - target).total_seconds()) <= 10800
        else fallback
    )
