"""Serialize decisions, confirmations, persistence and cancellable deadlines."""

import asyncio
import logging
import math
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    UnitOfTemperature,
)
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_state_report_event,
)
from homeassistant.util import dt as dt_util

from .const import CONF_HEATER, CONF_INDOOR
from .cycle_controller import CycleController, Decision
from .heater_adapter import SwitchAdapter
from .schedule import ScheduleResolution, WeekSchedule
from .settings import Settings
from .sources import configured_sources, resolve, temperature
from .storage import ControlStore

_LOGGER = logging.getLogger(__name__)


class ControlRuntime:
    """One runtime per zone; no overlapping command or persistence operations."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, changed: Callable[[], None]
    ) -> None:
        self.hass, self.entry, self.changed = hass, entry, changed
        self.sources = configured_sources(entry)
        self.settings = Settings.from_dict(dict(entry.options.get("settings", {})))
        self.core = CycleController(self.settings, hass.loop.time)
        self.adapter = SwitchAdapter(
            hass, self.sources[CONF_HEATER], self.settings.inverted
        )
        self.store = ControlStore(hass, entry.entry_id)
        self.schedule = self._schedule_from_options()
        self.mode = "off"
        self.heat = False
        self.manual_target = self.settings.initial_target
        self.target = self.manual_target
        self.override: tuple[float, datetime] | None = None
        self.schedule_resolution: ScheduleResolution | None = None
        self.decision = Decision("reconciling")
        self.indoor: float | None = None
        self.expires: float | None = None
        self._report: tuple[str | None, datetime] | None = None
        self._timer: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._source_listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task[None] | None = None
        self._dirty = False
        self._running = False
        self._ready = hass.state == CoreState.running
        self._in_flight = False
        self._last_saved: dict[str, Any] | None = None
        self._logged_fault: str | None = None

    def _schedule_from_options(self) -> WeekSchedule:
        value = self.entry.options.get("schedule")
        if value is None:
            return WeekSchedule.default(self.settings.initial_target)
        if not isinstance(value, dict):
            raise ValueError("Invalid schedule")
        return WeekSchedule.from_dict(value)

    def _local_now(self) -> datetime:
        return dt_util.now(dt_util.get_time_zone(self.hass.config.time_zone))

    def _apply_mode(self) -> float | None:
        """Resolve AUTO once per decision and return its next deadline delay."""
        now = self._local_now()
        self.schedule_resolution = self.schedule.resolve(now)
        if self.override is not None and now >= self.override[1]:
            self.override = None
        if self.mode == "auto":
            self.heat = True
            self.target = (
                self.override[0]
                if self.override is not None
                else self.schedule_resolution.current.temperature
            )
        else:
            self.heat = self.mode == "heat"
            self.target = self.manual_target
        return max(0.0, (self.schedule_resolution.next_at - now).total_seconds())

    def set_mode(self, mode: str) -> None:
        """Set a user mode; AUTO starts from the current schedule target."""
        if mode not in {"off", "heat", "auto"}:
            raise ValueError("Unsupported mode")
        if mode == "auto" and self.mode != "auto":
            self.override = None
        self.mode = mode
        self.request()

    def set_target(self, target: float) -> None:
        """In AUTO, retain a manual target only up to the next schedule point."""
        if self.mode == "auto":
            resolution = self.schedule.resolve(self._local_now())
            self.override = (target, resolution.next_at)
        else:
            self.manual_target = target
        self.request()

    async def start(self) -> None:
        """Load the safety record before any control decision."""
        try:
            saved = await self.store.async_load()
            if saved is not None:
                self._restore(saved)
        except Exception:
            # Do not print store contents, entity names, or exception payloads.
            self.core.fail("storage_invalid")
        self._running = True
        self._listeners.append(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._registry_changed
            )
        )
        if not self._ready:
            self._listeners.append(
                self.hass.bus.async_listen_once(
                    EVENT_HOMEASSISTANT_STARTED, self._started
                )
            )
        self._subscribe()
        self.request()

    def _restore(self, saved: dict[str, Any]) -> None:
        if (
            saved.get("schema_version") != 1
            or type(saved.get("pending")) is not bool
            or type(saved.get("heat")) is not bool
            or type(saved.get("observation_only")) is not bool
        ):
            raise ValueError("Invalid storage")
        target = saved["target"]
        if (
            isinstance(target, bool)
            or not isinstance(target, (int, float))
            or not math.isfinite(target)
        ):
            raise ValueError("Invalid target")
        fault = saved.get("fault")
        if fault is not None and fault not in {
            "command_timeout",
            "command_failed",
            "actuator_unavailable",
            "storage_invalid",
            "storage_failed",
            "command_interrupted",
        }:
            raise ValueError("Invalid fault")
        reset = self.entry.options.get("reset_fault_token")
        if reset == saved.get("reset_fault_token"):
            if fault:
                self.core.fail(fault)
            elif saved["pending"]:
                self.core.fail("command_interrupted")
        if saved.get("sources") == self.sources:
            target = min(
                self.settings.max_temperature,
                max(self.settings.min_temperature, float(target)),
            )
            self.manual_target = target
            self.target = target
            mode = saved.get("mode", "heat" if saved["heat"] else "off")
            if mode not in {"off", "heat", "auto"}:
                raise ValueError("Invalid mode")
            override = saved.get("override")
            if override is not None:
                try:
                    override_target = float(override["target"])
                    override_until = datetime.fromisoformat(override["until"])
                except (KeyError, TypeError, ValueError) as err:
                    raise ValueError("Invalid override") from err
                if (
                    not math.isfinite(override_target)
                    or override_until.tzinfo is None
                    or not self.settings.min_temperature
                    <= override_target
                    <= self.settings.max_temperature
                ):
                    raise ValueError("Invalid override")
                if override_until > self._local_now():
                    self.override = (override_target, override_until)
            # Enabling hardware never resumes a dry-run demand automatically.
            if saved["observation_only"] == self.settings.observation_only:
                self.mode = mode

    def _snapshot(self, pending: bool = False) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "heat": self.heat,
            "target": self.target,
            "manual_target": self.manual_target,
            "mode": self.mode,
            "override": None
            if self.override is None
            else {"target": self.override[0], "until": self.override[1].isoformat()},
            "fault": self.core.fault,
            "pending": pending or self._in_flight or self.core.pending is not None,
            "sources": self.sources,
            "observation_only": self.settings.observation_only,
            "reset_fault_token": self.entry.options.get("reset_fault_token"),
        }

    async def _save(self, pending: bool = False) -> bool:
        snapshot = self._snapshot(pending)
        if snapshot == self._last_saved:
            return True
        try:
            await self.store.async_save(snapshot)
        except Exception:
            self.core.fail("storage_failed")
            return False
        self._last_saved = snapshot
        return True

    @callback
    def _started(self, event: Event[Any]) -> None:
        self._ready = True
        self.request()

    @callback
    def _subscribe(self) -> None:
        for remove in self._source_listeners:
            remove()
        ids = [
            value for ref in self.sources.values() if (value := resolve(self.hass, ref))
        ]
        self._source_listeners = [
            async_track_state_change_event(self.hass, ids, self._source_changed),
            async_track_state_report_event(self.hass, ids, self._source_changed),
        ]

    @callback
    def _registry_changed(self, event: Event[Any]) -> None:
        self._subscribe()
        self.request()

    @callback
    def _source_changed(self, event: Event[Any]) -> None:
        # Record every actuator transition, even while service I/O is awaiting.
        if self._ready and event.data["entity_id"] == resolve(
            self.hass, self.sources[CONF_HEATER]
        ):
            state = event.data.get("new_state")
            value = None
            if (
                state is not None
                and not state.attributes.get("restored")
                and state.state in ("on", "off")
            ):
                value = (state.state == "on") != self.settings.inverted
            self.core.observe(value)
        self.request()

    @callback
    def request(self) -> None:
        if not self._running:
            return
        self._dirty = True
        if self._task is None or self._task.done():
            self._task = self.hass.async_create_task(
                self._drain(), "predictive thermostat decision", eager_start=False
            )

    def _read(self) -> None:
        self.core.observe(self.adapter.observed())
        entity_id = resolve(self.hass, self.sources[CONF_INDOOR])
        state = self.hass.states.get(entity_id) if entity_id else None
        self.indoor = temperature(self.hass, entity_id, UnitOfTemperature.CELSIUS)
        if state is None or state.attributes.get("restored"):
            self.indoor = None
            self.expires = None
            self._report = None
            return
        report = (entity_id, state.last_reported)
        if report != self._report:
            self._report = report
            age = max(0.0, (dt_util.utcnow() - state.last_reported).total_seconds())
            self.expires = self.core.clock() + max(
                0.0, self.settings.sensor_max_age - age
            )
        if self.expires is not None and self.core.clock() >= self.expires:
            self.indoor = None

    async def _drain(self) -> None:
        while self._dirty and self._running:
            self._dirty = False
            await self._evaluate()

    async def _evaluate(self) -> None:
        if not self._ready:
            return
        if self._timer:
            self._timer()
            self._timer = None
        self._read()
        schedule_delay = self._apply_mode()
        self.decision = self.core.decide(self.heat, self.target, self.indoor)
        command = self.decision.command
        if command is not None and not self.settings.observation_only:
            # Persist before sending: a crash can never silently retry this intent.
            if await self._save(pending=True):
                # Source, temperature or mode may have changed while writing storage.
                self._read()
                current = self.core.decide(self.heat, self.target, self.indoor)
                if self._running and current.command is command:
                    self.core.start_command(command)
                    self._in_flight = True
                    try:
                        async with asyncio.timeout(self.settings.command_timeout):
                            await self.adapter.command(command)
                    except TimeoutError:
                        self.core.fail("command_timeout")
                    except Exception:
                        self.core.fail("command_failed")
                    finally:
                        self._in_flight = False
                    self._read()
        self.decision = self.core.decide(self.heat, self.target, self.indoor)
        await self._save()
        self.decision = self.core.decide(self.heat, self.target, self.indoor)
        if self.core.fault and self.core.fault != self._logged_fault:
            _LOGGER.error(
                "Heater control stopped: %s; explicit fault reset required",
                self.core.fault,
            )
            self._logged_fault = self.core.fault
        now = self.core.clock()
        deadlines = [
            d
            for d in (self.decision.deadline, self.expires)
            if d is not None and d > now
        ]
        if schedule_delay is not None and schedule_delay > 0:
            deadlines.append(now + schedule_delay)
        if deadlines and self._running:
            self._timer = async_call_later(self.hass, min(deadlines) - now, self._wake)
        if self._running:
            self.changed()

    @callback
    def _wake(self, now: datetime) -> None:
        self._timer = None
        self.request()

    async def stop(self) -> None:
        """Cancel callbacks/tasks, save uncertainty, never command during unload."""
        self._running = False
        for remove in self._listeners + self._source_listeners:
            remove()
        if self._timer:
            self._timer()
            self._timer = None
        if self._in_flight:
            self.core.fail("command_interrupted")
        if self._task and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        await self._save()
