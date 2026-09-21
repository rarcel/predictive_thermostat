"""Weekly local-time targets, independent from Home Assistant and prediction."""

import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import Any

DAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_POINT = re.compile(r"^(?P<time>[0-2][0-9]:[0-5][0-9])\s*=\s*(?P<temp>.+)$")


@dataclass(frozen=True, order=True)
class SchedulePoint:
    """One target attached to a local wall-clock time."""

    at: time
    temperature: float


@dataclass(frozen=True)
class ScheduleResolution:
    """Target in force and the next nominal point occurrence."""

    current: SchedulePoint
    current_at: datetime
    next: SchedulePoint
    next_at: datetime


class WeekSchedule:
    """An immutable, complete weekly schedule in local time."""

    def __init__(self, points: dict[str, tuple[SchedulePoint, ...]]) -> None:
        if set(points) != set(DAYS) or any(not values for values in points.values()):
            raise ValueError("schedule_days")
        normalized: dict[str, tuple[SchedulePoint, ...]] = {}
        for day, values in points.items():
            ordered = tuple(sorted(values))
            if len({point.at for point in ordered}) != len(ordered):
                raise ValueError("schedule_duplicate")
            for point in ordered:
                if not math.isfinite(point.temperature):
                    raise ValueError("schedule_temperature")
            normalized[day] = ordered
        self.points = normalized

    @classmethod
    def default(cls, temperature: float) -> WeekSchedule:
        return cls({day: (SchedulePoint(time(0, 0), temperature),) for day in DAYS})

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> WeekSchedule:
        try:
            parsed = {
                day: tuple(
                    SchedulePoint(
                        time.fromisoformat(item["time"]), float(item["temperature"])
                    )
                    for item in value[day]
                )
                for day in DAYS
            }
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("schedule_format") from err
        if any(
            point.at.second or point.at.microsecond or point.at.tzinfo is not None
            for items in parsed.values()
            for point in items
        ):
            raise ValueError("schedule_time")
        return cls(parsed)

    def as_dict(self) -> dict[str, list[dict[str, float | str]]]:
        return {
            day: [
                {"time": point.at.strftime("%H:%M"), "temperature": point.temperature}
                for point in points
            ]
            for day, points in self.points.items()
        }

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> WeekSchedule:
        parsed: dict[str, tuple[SchedulePoint, ...]] = {}
        for day in DAYS:
            raw = fields[day]
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("schedule_empty")
            values: list[SchedulePoint] = []
            # A comma before a time separates entries; otherwise it is a French decimal.
            for item in re.split(r";|\n|,(?=\s*[0-2][0-9]:)", raw):
                match = _POINT.fullmatch(item.strip())
                if match is None:
                    raise ValueError("schedule_format")
                try:
                    at = time.fromisoformat(match["time"])
                    temperature = float(match["temp"].replace(",", "."))
                except ValueError as err:
                    raise ValueError("schedule_format") from err
                if at.hour > 23 or not math.isfinite(temperature):
                    raise ValueError("schedule_format")
                values.append(SchedulePoint(at, temperature))
            parsed[day] = tuple(values)
        return cls(parsed)

    def fields(self) -> dict[str, str]:
        return {
            day: ", ".join(
                f"{point.at:%H:%M}={point.temperature:g}" for point in points
            )
            for day, points in self.points.items()
        }

    def resolve(self, now: datetime) -> ScheduleResolution:
        """Resolve dates from wall time; repeated times run once at first occurrence."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("schedule_timezone")
        occurrences: list[tuple[datetime, datetime, SchedulePoint]] = []
        for offset in range(-8, 9):
            local_date = now.date() + timedelta(days=offset)
            for point in self.points[DAYS[local_date.weekday()]]:
                occurrence, nominal = self._occurrence(local_date, point.at, now.tzinfo)
                occurrences.append((occurrence, nominal, point))
        before = [item for item in occurrences if item[0] <= now]
        after = [item for item in occurrences if item[0] > now]
        current_at, _, current = max(before, key=lambda item: (item[0], item[1]))
        next_at, _, next_point = min(after, key=lambda item: (item[0], item[1]))
        return ScheduleResolution(current, current_at, next_point, next_at)

    @staticmethod
    def _occurrence(
        local_date: date, local_time: time, zone: tzinfo
    ) -> tuple[datetime, datetime]:
        nominal = datetime.combine(local_date, local_time, zone)
        # A nonexistent wall time is shifted to the first valid local instant.
        occurrence = nominal.astimezone(UTC).astimezone(zone)
        return occurrence, nominal
