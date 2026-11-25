# Modified for MB Scene Creator (2026): independent integration namespace.
"""Time of day (3.7): the phases day, dusk and night, and scenes that stand for another scene per phase."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from astral import Observer

from homeassistant.core import HomeAssistant

from custom_components.mb_scene_creator import daytime as dm
from custom_components.mb_scene_creator.daytime import limits_of, next_changes, normalize, phase_at

from .test_custom_presets import setup, userdata, runtime  # noqa: F401  (fixture and helpers)
from .test_music_scenes import fake_lights, on

TZ = ZoneInfo("Europe/Zurich")
BERN = Observer(46.95, 7.48, 0)
DAYTIME = "d4a1f7c0-6b3e-4e52-8c1d-2f9a7b5e0c63"
LIGHTS = ["light.a", "light.b"]
OTHER = ["light.c"]
# night when the sun is below -25 degrees, but not before 22:00 and at the latest at 23:30
WINDOW = normalize({
    "dusk": {"elevation": 0},
    "night": {"elevation": -25, "earliest": "22:00", "latest": "23:30"},
    "day": {"elevation": 0, "earliest": "06:30", "latest": "08:30"},
})
SUN_ONLY = normalize({"dusk": {"elevation": 0}, "night": {"elevation": -25, "latest": None}, "day": {"elevation": 0}})


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def at(month, day, hour, minute=0):
    return dt.datetime(2026, month, day, hour, minute, tzinfo=TZ)


@pytest.mark.parametrize(("when", "expected"), [
    # winter: sunset 16:41, -25 degrees at 19:17, sunrise 08:15
    (at(12, 21, 12), "day"),
    (at(12, 21, 17), "dusk"),
    (at(12, 21, 20), "dusk"),  # the sun is low enough, but night not before 22:00
    (at(12, 21, 22, 1), "night"),
    (at(12, 22, 3), "night"),
    (at(12, 22, 6), "dusk"),  # dawn: the sun is above -25 degrees again (05:39)
    (at(12, 22, 8, 20), "day"),
    # summer: the sun never gets to -25 degrees, sunset about 21:27, sunrise about 05:36
    (at(6, 21, 18), "day"),
    (at(6, 21, 22), "dusk"),
    (at(6, 21, 23, 29), "dusk"),
    (at(6, 21, 23, 31), "night"),  # at the latest
    (at(6, 22, 3), "night"),
    (at(6, 22, 6), "night"),  # the day does not begin before 06:30
    (at(6, 22, 6, 31), "day"),
])
def test_one_setting_for_summer_and_winter(when, expected):
    assert phase_at(BERN, WINDOW, when) == expected


def test_sun_only_is_the_same_in_the_morning_and_in_the_evening():
    assert phase_at(BERN, SUN_ONLY, at(12, 21, 20)) == "night"
    assert phase_at(BERN, SUN_ONLY, at(12, 22, 5)) == "night"
    assert phase_at(BERN, SUN_ONLY, at(12, 22, 7)) == "dusk"
    # summer without a time: it never gets night
    assert phase_at(BERN, SUN_ONLY, at(6, 22, 1)) == "dusk"
    assert phase_at(BERN, SUN_ONLY, at(6, 22, 12)) == "day"


def test_clock_only():
    config = normalize({
        "dusk": {"elevation": None, "earliest": "18:00"},
        "night": {"elevation": None, "earliest": "00:30"},  # after midnight
        "day": {"elevation": None, "earliest": "07:00"},
    })
    for when, expected in ((at(6, 21, 17, 59), "day"), (at(6, 21, 18), "dusk"), (at(6, 22, 0, 29), "dusk"),
                           (at(6, 22, 0, 30), "night"), (at(6, 22, 6, 59), "night"), (at(6, 22, 7), "day")):
        assert phase_at(BERN, config, when) == expected


def test_next_changes_and_limits():
    changes = next_changes(BERN, WINDOW, at(12, 21, 12), 3)
    assert [phase for phase, _ in changes] == ["dusk", "night", "dusk"]
    assert changes[0][1].strftime("%H:%M") == "16:41"
    assert changes[1][1].strftime("%d %H:%M") == "21 22:00"
    assert changes[2][1].strftime("%d %H:%M") == "22 05:39"
    limits = limits_of(BERN, WINDOW, dt.date(2026, 6, 21), TZ)
    assert limits.dawn is None and limits.night.strftime("%H:%M") == "23:30" and limits.day.strftime("%H:%M") == "06:30"


def test_normalize_repairs_a_configuration():
    config = normalize({"night": {"elevation": None, "earliest": None, "latest": None}, "day": {"elevation": 99, "earliest": "25:00"}, "x": 1})
    assert config["night"] == dm.DEFAULT_CONFIG["night"]  # a limit needs the sun or a time
    assert config["day"]["elevation"] == 60 and config["day"]["earliest"] is None
    assert config["dusk"] == dm.DEFAULT_CONFIG["dusk"]


# ---------------------------------------------------------------- scenes

async def scenes(hass, monkeypatch, follow=False, **phases):
    await setup(hass, monkeypatch)
    fake_lights(hass, LIGHTS + OTHER)
    ids = {}
    import custom_components.mb_scene_creator.file_utils as fu

    presets = [p["id"] for p in fu.PRESET_DATA["presets"] if not p.get("music") and not p.get("daytime")]
    for index, name in enumerate(("day", "dusk", "night")):
        preset_id = presets[index]
        r = await hass.services.async_call("mb_scene_creator", "save_scene", {
            "name": name, "preset_id": preset_id, "targets": {"entity_id": LIGHTS}, "brightness": {"day": 250, "dusk": 150, "night": 20}[name],
        }, blocking=True, return_response=True)
        ids[name] = r["scene"]["id"]
    settings = {phase: ids[phase] for phase in (phases or {"day": 1, "dusk": 1, "night": 1})}
    r = await hass.services.async_call("mb_scene_creator", "save_scene", {
        "name": "Auto", "preset_id": DAYTIME, "targets": {"entity_id": LIGHTS},
        "daytime": {**settings, "follow": follow},
    }, blocking=True, return_response=True)
    return r["scene"]["id"], ids


def set_phase(hass, monkeypatch, phase):
    monkeypatch.setattr(dm, "phase_at", lambda *a, **k: phase)
    runtime(hass).daytime._update()


def brightness(hass, light="light.a"):
    return hass.states.get(light).attributes.get("brightness")


async def activate(hass, scene_id, **extra):
    await hass.services.async_call("mb_scene_creator", "activate_saved_scene", {"id": scene_id, **extra}, blocking=True)
    await hass.async_block_till_done()


async def test_scene_of_the_current_phase(hass: HomeAssistant, monkeypatch, userdata):
    auto, _ = await scenes(hass, monkeypatch)
    for phase, expected in (("day", 250), ("dusk", 150), ("night", 20)):
        set_phase(hass, monkeypatch, phase)
        await activate(hass, auto)
        assert brightness(hass) == expected and brightness(hass, "light.b") == expected
    assert hass.states.get("sensor.mb_scene_creator_time_of_day").state == "night"
    assert runtime(hass).daytime.following() == []  # without "follow" nothing stays active


async def test_missing_phase_uses_the_phase_before(hass: HomeAssistant, monkeypatch, userdata):
    auto, _ = await scenes(hass, monkeypatch, day=1)
    set_phase(hass, monkeypatch, "night")
    await activate(hass, auto)
    assert brightness(hass) == 250
    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)

    auto2, _ = None, None
    r = await hass.services.async_call("mb_scene_creator", "save_scene", {
        "name": "Empty", "preset_id": DAYTIME, "targets": {"entity_id": LIGHTS}, "daytime": {},
    }, blocking=True, return_response=True)
    await activate(hass, r["scene"]["id"])  # nothing set: nothing happens, no error
    assert not on(hass, "light.a")


async def test_on_one_lamp_only(hass: HomeAssistant, monkeypatch, userdata):
    auto, _ = await scenes(hass, monkeypatch)
    set_phase(hass, monkeypatch, "night")
    await activate(hass, auto, targets={"entity_id": OTHER})
    assert brightness(hass, "light.c") == 20 and not on(hass, "light.a")


async def test_follow_changes_with_the_phase_until_another_scene_or_lights_off(
    hass: HomeAssistant, monkeypatch, userdata
):
    auto, ids = await scenes(hass, monkeypatch, follow=True)
    daytime = runtime(hass).daytime
    set_phase(hass, monkeypatch, "dusk")
    await activate(hass, auto)
    assert brightness(hass) == 150 and daytime.following() == [auto]

    set_phase(hass, monkeypatch, "night")
    await hass.async_block_till_done()
    assert brightness(hass) == 20 and daytime.following() == [auto]

    # another scene on these lights: the time of day scene is over
    await activate(hass, ids["day"])
    assert brightness(hass) == 250 and daytime.following() == []
    set_phase(hass, monkeypatch, "dusk")
    await hass.async_block_till_done()
    assert brightness(hass) == 250

    # lights off: over as well
    await activate(hass, auto)
    assert daytime.following() == [auto]
    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()
    assert daytime.following() == []
    set_phase(hass, monkeypatch, "night")
    await hass.async_block_till_done()
    assert not on(hass, "light.a")

    # the stop services and a scene of Home Assistant end it too
    await activate(hass, auto)
    await hass.services.async_call("mb_scene_creator", "stop_all_dynamic_scenes", {}, blocking=True)
    assert daytime.following() == []
    await activate(hass, auto)
    hass.bus.async_fire("call_service", {
        "domain": "scene", "service": "apply", "service_data": {"entities": {"light.a": {"state": "on"}}}})
    await hass.async_block_till_done()
    assert daytime.following() == []


async def test_settings_over_websocket(hass: HomeAssistant, monkeypatch, userdata, hass_ws_client):
    await setup(hass, monkeypatch)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "mb_scene_creator/get_daytime"})
    result = (await client.receive_json())["result"]
    assert result["phase"] in ("day", "dusk", "night") and result["config"] == dm.DEFAULT_CONFIG and result["next"]

    await client.send_json({"id": 2, "type": "mb_scene_creator/set_daytime", "config": {
        "night": {"elevation": -25, "earliest": "22:00", "latest": "23:30"}}})
    result = (await client.receive_json())["result"]
    assert result["config"]["night"] == {"elevation": -25.0, "earliest": "22:00", "latest": "23:30"}
    assert runtime(hass).daytime.config["night"]["earliest"] == "22:00"
