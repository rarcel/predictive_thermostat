"""Weekly planning tests including local-time DST rules."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.predictive_thermostat.schedule import DAYS, WeekSchedule


@pytest.fixture
def schedule():
    return WeekSchedule.from_fields(
        {day: "06:30=19, 18:00=21" if day == "monday" else "00:00=17" for day in DAYS}
    )


def test_current_next_and_week_boundary(schedule):
    zone = ZoneInfo("Europe/Paris")
    result = schedule.resolve(datetime(2026, 9, 21, 7, 0, tzinfo=zone))
    assert (result.current.temperature, result.next.temperature) == (19, 21)
    result = schedule.resolve(datetime(2026, 9, 27, 23, 0, tzinfo=zone))
    assert result.next_at == datetime(2026, 9, 28, 6, 30, tzinfo=zone)


def test_empty_duplicate_and_invalid_schedules_are_rejected():
    fields = {day: "00:00=18" for day in DAYS}
    fields["monday"] = ""
    with pytest.raises(ValueError):
        WeekSchedule.from_fields(fields)
    fields["monday"] = "07:00=18,07:00=20"
    with pytest.raises(ValueError):
        WeekSchedule.from_fields(fields)
    fields["monday"] = "bad"
    with pytest.raises(ValueError):
        WeekSchedule.from_fields(fields)


def test_spring_gap_moves_to_first_valid_instant():
    fields = {day: "00:00=17" for day in DAYS}
    fields["sunday"] = "02:30=20, 03:00=21"
    schedule = WeekSchedule.from_fields(fields)
    zone = ZoneInfo("Europe/Paris")
    result = schedule.resolve(datetime(2026, 3, 29, 3, 1, tzinfo=zone))
    # Both points occur at 03:00; the later nominal point wins deterministically.
    assert result.current.temperature == 21


def test_fall_repeated_time_runs_once_at_first_occurrence():
    fields = {day: "00:00=17" for day in DAYS}
    fields["sunday"] = "02:30=20, 04:00=21"
    schedule = WeekSchedule.from_fields(fields)
    zone = ZoneInfo("Europe/Paris")
    second_0230 = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)
    result = schedule.resolve(second_0230)
    assert result.current.temperature == 20
    assert result.next.temperature == 21
