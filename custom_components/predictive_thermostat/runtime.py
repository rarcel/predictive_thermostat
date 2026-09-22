"""Serialize decisions, confirmations, persistence and cancellable deadlines."""

import asyncio
import logging
import math
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import persistent_notification
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

from .const import CONF_HEATER, CONF_INDOOR, CONF_OUTDOOR, CONF_WEATHER, DOMAIN
from .cycle_controller import CycleController, Decision
from .heater_adapter import SwitchAdapter
from .model import FallbackModel, LearningState, Prediction
from .observations import HeatingCycle
from .schedule import ScheduleResolution, WeekSchedule
from .settings import Settings
from .sources import configured_sources, resolve, temperature
from .storage import ControlStore
from .weather import async_forecast_temperature

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
        self.learning = LearningState.initial(self.settings)
        self.model = FallbackModel(self.settings, self.learning)
        self.mode = "off"
        self.heat = False
        self.manual_target = self.settings.initial_target
        self.target = self.manual_target
        self.override: tuple[float, datetime] | None = None
        self.schedule_resolution: ScheduleResolution | None = None
        self.outdoor: float | None = None
        self.forecast_outdoor: float | None = None
        self.prediction: Prediction | None = None
        self.predicted_start: datetime | None = None
        self.preheating = False
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
        self._cycle_started: tuple[float, float, float, float] | None = None
        self._arrival_recorded_for: datetime | None = None
        self._indoor_alert_active = False
        self._fault_alert_active = False
        self.heater_available = False
        self._actuator_unavailable_since: float | None = None

    @property
    def _indoor_notification_id(self) -> str:
        """Return the stable ID for this zone's source-data alert."""
        return f"{DOMAIN}_{self.entry.entry_id}_indoor_sensor"

    @property
    def _fault_notification_id(self) -> str:
        """Return the stable ID for this zone's safety-fault alert."""
        return f"{DOMAIN}_{self.entry.entry_id}_fault"

    def _update_indoor_sensor_notification(self) -> None:
        """Expose an actionable, deduplicated alert for missing indoor data."""
        if self.indoor is not None:
            if self._indoor_alert_active:
                persistent_notification.async_dismiss(
                    self.hass, self._indoor_notification_id
                )
                self._indoor_alert_active = False
            return
        if self._indoor_alert_active:
            return
        if self.hass.config.language.startswith("fr"):
            title = "Thermostat prédictif suspendu"
            message = (
                f"La sonde intérieure de la zone « {self.entry.title} » est "
                "indisponible ou périmée. Les nouvelles demandes de chauffe sont "
                "suspendues jusqu'à la prochaine mesure valide."
            )
        else:
            title = "Predictive Thermostat paused"
            message = (
                f"The indoor sensor for zone '{self.entry.title}' is unavailable "
                "or stale. New heating requests are paused until a valid reading "
                "is received."
            )
        persistent_notification.async_create(
            self.hass,
            message,
            title=title,
            notification_id=self._indoor_notification_id,
        )
        self._indoor_alert_active = True

    def _update_fault_notification(self) -> None:
        """Expose a latched control fault in Home Assistant's notification center."""
        fault = self.core.fault
        if fault is None:
            if self._fault_alert_active:
                persistent_notification.async_dismiss(
                    self.hass, self._fault_notification_id
                )
                self._fault_alert_active = False
            return
        if self._fault_alert_active:
            return
        if self.hass.config.language.startswith("fr"):
            title = "Thermostat prédictif en sécurité"
            message = (
                f"La zone « {self.entry.title} » est verrouillée après le défaut "
                f"« {fault} ». Vérifiez l'actionneur puis acquittez le défaut dans "
                "les options de l'intégration."
            )
        else:
            title = "Predictive Thermostat safety lock"
            message = (
                f"Zone '{self.entry.title}' is locked after '{fault}'. Check the "
                "actuator, then acknowledge the fault in the integration options."
            )
        persistent_notification.async_create(
            self.hass,
            message,
            title=title,
            notification_id=self._fault_notification_id,
        )
        self._fault_alert_active = True

    def _schedule_from_options(self) -> WeekSchedule:
        value = self.entry.options.get("schedule")
        if value is None:
            return WeekSchedule.default(self.settings.initial_target)
        if not isinstance(value, dict):
            raise ValueError("Invalid schedule")
        return WeekSchedule.from_dict(value)

    def _local_now(self) -> datetime:
        return dt_util.now(dt_util.get_time_zone(self.hass.config.time_zone))

    def _apply_mode(self) -> list[float]:
        """Resolve AUTO and return local schedule/prediction deadline delays."""
        now = self._local_now()
        self.schedule_resolution = self.schedule.resolve(now)
        deadlines = [(self.schedule_resolution.next_at - now).total_seconds()]
        self.prediction = None
        self.predicted_start = None
        self.preheating = False
        if self.override is not None and now >= self.override[1]:
            self.override = None
        if self.mode == "auto":
            self.heat = True
            self.target = self.schedule_resolution.current.temperature
            if self.override is not None:
                self.target = self.override[0]
            elif (
                self.schedule_resolution.next.temperature
                > self.schedule_resolution.current.temperature
            ):
                self.prediction = self.model.predict(
                    self.indoor,
                    self.forecast_outdoor
                    if self.forecast_outdoor is not None
                    else self.outdoor,
                    self.schedule_resolution.next.temperature,
                )
                if self.prediction is not None:
                    self.predicted_start = self.schedule_resolution.next_at - timedelta(
                        minutes=self.prediction.minutes
                    )
                    if now >= self.predicted_start:
                        self.target = self.schedule_resolution.next.temperature
                        self.preheating = now < self.schedule_resolution.next_at
                        if (
                            self.indoor is not None
                            and self.indoor >= self.target
                            and self._arrival_recorded_for
                            != self.schedule_resolution.next_at
                        ):
                            error = (
                                now - self.schedule_resolution.next_at
                            ).total_seconds() / 60
                            self.learning = self.learning.record_arrival_error(error)
                            self.model = FallbackModel(self.settings, self.learning)
                            self._arrival_recorded_for = (
                                self.schedule_resolution.next_at
                            )
                    else:
                        deadlines.append((self.predicted_start - now).total_seconds())
            if (
                self.settings.optimal_stop_enabled
                and self.schedule_resolution.next.temperature < self.target
                and self.indoor is not None
            ):
                coast = (
                    self.indoor - self.schedule_resolution.next.temperature
                ) / self.settings.cooling_rate
                if 0 <= coast and (
                    self.schedule_resolution.next_at - now
                ).total_seconds() / 60 <= min(coast, self.settings.max_stop_advance):
                    self.heat = False
        else:
            self.heat = self.mode == "heat"
            self.target = self.manual_target
        return [delay for delay in deadlines if delay > 0]

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
        # Home Assistant may call the platform setup again while a registry
        # change is being processed.  Keep the existing listeners in that
        # case: registering them twice makes their unsubscribe callbacks
        # invalid and can prevent the climate entity from being added.
        if self._running:
            return
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
            learning = saved.get("learning")
            if learning is not None:
                if not isinstance(learning, dict):
                    raise ValueError("Invalid learning")
                self.learning = LearningState.from_dict(learning, self.settings)
                self.model = FallbackModel(self.settings, self.learning)
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
            "learning": self.learning.as_dict(),
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
        # Clear the list before invoking callbacks. A callback can already
        # have been consumed by Home Assistant during an entry reload; it is
        # then harmless, but must not stop rebuilding the subscriptions.
        listeners, self._source_listeners = self._source_listeners, []
        for remove in listeners:
            try:
                remove()
            except ValueError:
                # Home Assistant listener removal is not idempotent. This
                # happens after a registry-driven reload, not a control error.
                pass
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
        observed = self.adapter.observed()
        self.heater_available = observed is not None
        if observed is None:
            now = self.core.clock()
            if self._actuator_unavailable_since is None:
                self._actuator_unavailable_since = now
            elif (
                now - self._actuator_unavailable_since
                >= self.settings.command_timeout
            ):
                # A source can briefly be unavailable while Home Assistant or
                # its integration reloads. Do not turn that reconciliation
                # period into a permanent fault, but lock a sustained loss.
                self.core.observe(None)
        else:
            self._actuator_unavailable_since = None
            self.core.observe(observed)
            if self.core.recover_actuator_unavailable():
                # A confirmed source state restarts the normal min-off/min-on
                # protections. Other fault types still require acknowledgement.
                self._logged_fault = None
        entity_id = resolve(self.hass, self.sources[CONF_INDOOR])
        state = self.hass.states.get(entity_id) if entity_id else None
        self.indoor = temperature(self.hass, entity_id, UnitOfTemperature.CELSIUS)
        self.outdoor = temperature(
            self.hass,
            resolve(self.hass, self.sources[CONF_OUTDOOR]),
            UnitOfTemperature.CELSIUS,
        )
        if state is None or state.attributes.get("restored"):
            self.indoor = None
            self.expires = None
            self._report = None
            self._update_indoor_sensor_notification()
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
        self._update_indoor_sensor_notification()
        self._learn_cycle()

    def _learn_cycle(self) -> None:
        """Aggregate only a confirmed, plausible cycle that reached its target."""
        if self.core.observed and self._cycle_started is None:
            if self.indoor is not None and self.outdoor is not None:
                self._cycle_started = (
                    self.core.clock(),
                    self.indoor,
                    self.outdoor,
                    self.target,
                )
            return
        if self.core.observed or self._cycle_started is None:
            return
        started, indoor, outdoor, target = self._cycle_started
        self._cycle_started = None
        if self.indoor is not None and self.indoor >= target:
            cycle = HeatingCycle(
                indoor, outdoor, target, (self.core.clock() - started) / 60
            )
            self.learning = self.learning.update(cycle).update_losses(
                cycle, self.settings
            )
            self.model = FallbackModel(self.settings, self.learning)

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
        next_at = self.schedule.resolve(self._local_now()).next_at
        weather = self.entry.options.get(CONF_WEATHER)
        weather_entity = (
            resolve(self.hass, weather) if isinstance(weather, dict) else None
        )
        self.forecast_outdoor = await async_forecast_temperature(
            self.hass,
            weather_entity,
            next_at,
            self.outdoor,
        )
        schedule_delays = self._apply_mode()
        self.decision = self._decide()
        command = self.decision.command
        if command is not None and not self.settings.observation_only:
            # Persist before sending: a crash can never silently retry this intent.
            if await self._save(pending=True):
                # Source, temperature or mode may have changed while writing storage.
                self._read()
                current = self._decide()
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
        self.decision = self._decide()
        await self._save()
        self.decision = self._decide()
        self._update_fault_notification()
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
        if (
            self._actuator_unavailable_since is not None
            and self.core.fault is None
        ):
            deadlines.append(
                self._actuator_unavailable_since + self.settings.command_timeout
            )
        deadlines.extend(now + delay for delay in schedule_delays)
        if deadlines and self._running:
            self._timer = async_call_later(self.hass, min(deadlines) - now, self._wake)
        if self._running:
            self.changed()

    def _decide(self) -> Decision:
        """Block commands while an actuator source is being reconciled."""
        if not self.heater_available and self.core.fault is None:
            return Decision("reconciling")
        return self.core.decide(self.heat, self.target, self.indoor)

    @callback
    def _wake(self, now: datetime) -> None:
        self._timer = None
        self.request()

    async def stop(self) -> None:
        """Cancel callbacks/tasks, save uncertainty, never command during unload."""
        self._running = False
        listeners = self._listeners + self._source_listeners
        self._listeners = []
        self._source_listeners = []
        for remove in listeners:
            try:
                remove()
            except ValueError:
                # A one-shot or registry listener may already be removed by
                # Home Assistant while an entry reload is in progress.
                pass
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
