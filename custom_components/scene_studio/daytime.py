"""Time of day (Scene Studio 3.7): day, dusk and night, and scenes that follow them.

Three phases in a fixed order: day -> dusk -> night -> (dawn, shown as dusk) -> day. Each of the three
limits (dusk begins, night begins, day begins) is the sun passing an elevation, optionally not before
``earliest`` and at the latest at ``latest`` (clock times). So one setting works in summer and in
winter: "night when the sun is below -25 degrees, but not before 22:00 and at the latest at 23:30".
A limit without an elevation is a clock time only.

The limits of a day are computed as points in time (astral), which makes the phase exact, lets the
panel show today's times and lets scenes change at the right moment.

A time of day scene is a saved scene with the preset ``DAYTIME_PRESET_ID`` and the setting
``daytime``: one other saved scene per phase and ``follow``. Activating it activates the scene of the
current phase. With ``follow`` it stays active and changes to the next scene when the phase changes,
as long as its lights are on and no other scene was started on them.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from dataclasses import dataclass

from astral import Observer, SunDirection
from astral.sun import time_at_elevation

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DAYTIME_PRESET_ID, DOMAIN
from .util import resolve_entity_ids

_LOGGER = logging.getLogger(__name__)

PHASES = ("day", "dusk", "night")
# a phase without a scene uses the scene of the phase before it
FALLBACK = {"night": ("night", "dusk", "day"), "dusk": ("dusk", "day"), "day": ("day",)}
DEFAULT_CONFIG = {
    "dusk": {"elevation": 0.0, "earliest": None, "latest": None},
    "night": {"elevation": -18.0, "earliest": None, "latest": "23:30"},
    "day": {"elevation": 0.0, "earliest": None, "latest": None},
}
FOLLOW_TRANSITION = 30  # seconds, a scene that follows the time of day changes slowly

STORAGE_KEY = f"{DOMAIN}.daytime"
STORAGE_VERSION = 1


def is_daytime_scene(scene: dict | None) -> bool:
    return bool(scene) and scene.get("preset_id") == DAYTIME_PRESET_ID


@dataclass
class Limits:
    """The limits that belong to one calendar day."""

    dawn: dt.datetime | None  # morning: the sun rises above the night elevation (dusk until the day begins)
    day: dt.datetime  # morning: the day begins
    dusk: dt.datetime | None  # evening
    night: dt.datetime | None  # evening (may be after midnight)


def _clock(day: dt.date, value: str | None, tz: dt.tzinfo, evening: bool) -> dt.datetime | None:
    if not value:
        return None
    hour, minute = (int(part) for part in value.split(":")[:2])
    # an evening time before noon means after midnight
    if evening and hour < 12:
        day = day + dt.timedelta(days=1)
    return dt.datetime.combine(day, dt.time(hour, minute), tz)


def _crossing(observer: Observer, elevation: float | None, day: dt.date, tz: dt.tzinfo, evening: bool):
    """When the sun passes this elevation in the evening (going down) or the morning (rising) of the day."""
    if elevation is None:
        return None
    noon = dt.datetime.combine(day, dt.time(12), tz)
    lo, hi = (noon, noon + dt.timedelta(days=1)) if evening else (noon - dt.timedelta(days=1), noon)
    direction = SunDirection.SETTING if evening else SunDirection.RISING
    for candidate in (day, day + dt.timedelta(days=1 if evening else -1)):
        try:
            when = time_at_elevation(observer, elevation, candidate, direction, tz)
        except ValueError:  # the sun does not get there on this day
            continue
        if lo <= when < hi:
            return when
    return None


def _limit(observer: Observer, rule: dict, day: dt.date, tz: dt.tzinfo, evening: bool) -> dt.datetime | None:
    earliest = _clock(day, rule.get("earliest"), tz, evening)
    latest = _clock(day, rule.get("latest"), tz, evening)
    if rule.get("elevation") is None:
        return earliest or latest
    when = _crossing(observer, rule["elevation"], day, tz, evening)
    if when is None:
        return latest  # the sun never gets there (summer): only "at the latest" starts the phase
    if earliest and when < earliest:
        when = earliest
    if latest and when > latest:
        when = latest
    return when


def limits_of(observer: Observer, config: dict, day: dt.date, tz: dt.tzinfo) -> Limits:
    start = _limit(observer, config["day"], day, tz, False) or dt.datetime.combine(day, dt.time(12), tz)
    dawn = _crossing(observer, config["night"].get("elevation"), day, tz, False)
    if dawn is not None and dawn >= start:
        dawn = None
    dusk = _limit(observer, config["dusk"], day, tz, True)
    night = _limit(observer, config["night"], day, tz, True)
    if dusk is not None and dusk < start:
        dusk = start
    if dusk is not None and night is not None and night < dusk:
        night = dusk
    return Limits(dawn, start, dusk, night)


def phase_at(observer: Observer, config: dict, now: dt.datetime) -> str:
    tz = now.tzinfo
    today = limits_of(observer, config, now.date(), tz)
    if now >= today.day:
        if today.dusk is None or now < today.dusk:
            return "day" if today.night is None or now < today.night else "night"
        return "dusk" if today.night is None or now < today.night else "night"
    # before the day begins: the evening of yesterday goes on
    yesterday = limits_of(observer, config, now.date() - dt.timedelta(days=1), tz)
    if yesterday.night is not None and now >= yesterday.night:
        return "dusk" if today.dawn is not None and now >= today.dawn else "night"
    if yesterday.dusk is not None and now >= yesterday.dusk:
        return "dusk"
    return "day"


def next_changes(observer: Observer, config: dict, now: dt.datetime, count: int = 3) -> list[tuple[str, dt.datetime]]:
    """The next changes of the phase as (new phase, when)."""
    tz = now.tzinfo
    moments: set[dt.datetime] = set()
    for offset in (-1, 0, 1, 2):
        limits = limits_of(observer, config, now.date() + dt.timedelta(days=offset), tz)
        moments.update(m for m in (limits.dawn, limits.day, limits.dusk, limits.night) if m is not None and m > now)
    changes, phase = [], phase_at(observer, config, now)
    for moment in sorted(moments):
        new = phase_at(observer, config, moment)
        if new != phase:
            changes.append((new, moment))
            phase = new
        if len(changes) >= count:
            break
    return changes


def normalize(config: dict | None) -> dict:
    """A complete, valid configuration (unknown or broken parts fall back to the default)."""
    result = {}
    for key, default in DEFAULT_CONFIG.items():
        rule = dict(default)
        given = (config or {}).get(key)
        if isinstance(given, dict):
            elevation = given.get("elevation", default["elevation"])
            rule["elevation"] = None if elevation is None else max(-60.0, min(60.0, float(elevation)))
            for field in ("earliest", "latest"):
                value = given.get(field, default[field])
                rule[field] = value if _valid_time(value) else None
            if rule["elevation"] is None and not rule["earliest"] and not rule["latest"]:
                rule = dict(default)  # a limit needs the sun or a time
        result[key] = rule
    return result


def _valid_time(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        hour, minute = (int(part) for part in value.split(":")[:2])
    except ValueError:
        return False
    return 0 <= hour < 24 and 0 <= minute < 60


@dataclass
class Follow:
    lights: list[str]
    targets: dict | None  # lamp mode: the scene was applied to these lights only
    unsub: CALLBACK_TYPE | None = None


class Daytime:
    """The current phase, its settings and the time of day scenes that follow it."""

    def __init__(self, hass: HomeAssistant, store, activate: Callable):
        self.hass = hass
        self.store = store  # saved scenes
        self._activate = activate  # async (scene, targets, transition) -> lights
        self._settings = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.config = normalize(None)
        self.phase = "day"
        self._listeners: list[Callable[[], None]] = []
        self._timer: CALLBACK_TYPE | None = None
        self._following: dict[str, Follow] = {}
        self._internal = False
        self._unsub_store = store.add_listener(self._on_store_change)

    async def async_load(self) -> None:
        self.config = normalize(await self._settings.async_load())
        self._update()

    async def async_set_config(self, config: dict) -> dict:
        self.config = normalize(config)
        await self._settings.async_save(self.config)
        self._update()
        return self.config

    @property
    def observer(self) -> Observer:
        return Observer(self.hass.config.latitude, self.hass.config.longitude, self.hass.config.elevation)

    def changes(self, count: int = 3) -> list[tuple[str, dt.datetime]]:
        return next_changes(self.observer, self.config, dt_util.now(), count)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def _update(self, _now=None) -> None:
        if self._timer:
            self._timer()
            self._timer = None
        old, now = self.phase, dt_util.now()
        self.phase = phase_at(self.observer, self.config, now)
        upcoming = next_changes(self.observer, self.config, now, 1)
        if upcoming:
            self._timer = async_track_point_in_time(self.hass, self._update, upcoming[0][1])
        for listener in list(self._listeners):
            listener()
        if self.phase != old and self._following:
            self.hass.async_create_task(self._follow_phase())

    # ------------------------------------------------------------------ scenes

    def scene_for(self, scene: dict, phase: str | None = None) -> dict | None:
        """The saved scene a time of day scene stands for right now (None: nothing set for this phase)."""
        settings = scene.get("daytime") or {}
        for candidate in FALLBACK[phase or self.phase]:
            target = self.store.get(settings.get(candidate) or "")
            if target is not None and not is_daytime_scene(target):
                return target
        return None

    async def async_activate(self, scene: dict, targets: dict | None = None, transition: int | None = None) -> None:
        target = self.scene_for(scene)
        if target is None:
            _LOGGER.warning("Time of day scene %s has no scene for %s", scene.get("name"), self.phase)
            return
        self._stop_following(scene["id"])
        self._internal = True
        try:
            lights = await self._activate(target, targets, transition)
        finally:
            self._internal = False
        if (scene.get("daytime") or {}).get("follow") and lights:
            follow = Follow(list(lights), targets)
            follow.unsub = async_track_state_change_event(self.hass, follow.lights, self._on_light)
            self._following[scene["id"]] = follow

    async def _follow_phase(self) -> None:
        for scene_id, follow in list(self._following.items()):
            scene = self.store.get(scene_id)
            if scene is None or not is_daytime_scene(scene):
                self._stop_following(scene_id)
                continue
            if self.scene_for(scene) is None:
                continue
            _LOGGER.debug("Time of day scene %s follows to %s", scene.get("name"), self.phase)
            await self.async_activate(scene, follow.targets, FOLLOW_TRANSITION)

    @callback
    def release_lights(self, lights) -> None:
        """Another scene was started on these lights (or they were stopped): do not follow any longer."""
        if self._internal or not self._following:
            return
        lights = set(lights)
        for entity_id in list(lights):
            lights.update(resolve_entity_ids(self.hass, entity_id))  # groups: their lights
        for scene_id, follow in list(self._following.items()):
            if lights & set(follow.lights):
                self._stop_following(scene_id)

    @callback
    def stop_all(self) -> None:
        if self._internal:
            return
        for scene_id in list(self._following):
            self._stop_following(scene_id)

    @callback
    def _on_light(self, _event: Event) -> None:
        for scene_id, follow in list(self._following.items()):
            states = [self.hass.states.get(entity_id) for entity_id in follow.lights]
            if not any(state is not None and state.state == "on" for state in states):
                self._stop_following(scene_id)  # all lights off: the scene is over

    @callback
    def _on_store_change(self, scene_id: str, scene: dict | None) -> None:
        if scene_id in self._following and not is_daytime_scene(scene):
            self._stop_following(scene_id)

    def _stop_following(self, scene_id: str) -> None:
        follow = self._following.pop(scene_id, None)
        if follow and follow.unsub:
            follow.unsub()

    def following(self) -> list[str]:
        return list(self._following)

    @callback
    def async_shutdown(self) -> None:
        if self._timer:
            self._timer()
            self._timer = None
        self._unsub_store()
        for scene_id in list(self._following):
            self._stop_following(scene_id)
