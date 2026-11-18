"""Music scenes: colors from the album cover, auto start and return to the state before."""

import io
from datetime import timedelta

import pytest
from PIL import Image
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .test_custom_presets import setup, userdata, runtime  # noqa: F401  (fixture and helpers)

PRESET = "e71b2ef3-1b15-4c4b-b036-4b3d6efe58f8"
MUSIC = "b1c7e3d2-2f4a-4c39-9d7e-6a1f0c5e8b42"
PLAYER = "media_player.living_room"
PLAYER_2 = "media_player.bedroom"
LIGHTS = ["light.a", "light.b"]
LIGHTS_2 = ["light.c"]
COVER = [(0.64, 0.33), (0.15, 0.06)]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def _image(colors):
    image = Image.new("RGB", (40, 40), colors[0])
    for i, color in enumerate(colors[1:], 1):
        image.paste(color, (0, i * 40 // len(colors), 40, 40))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def test_extract_cover_colors():
    from custom_components.scene_studio.music_scenes import extract_cover_colors

    colors = extract_cover_colors(_image([(220, 20, 30), (20, 40, 200)]))
    assert colors is not None and len(colors) >= 3  # two colors plus close variants
    assert extract_cover_colors(_image([(128, 128, 128), (10, 10, 10), (250, 250, 250)])) is None


def test_pale_cover_gives_vivid_colors():
    """A muted cover keeps its hue but the lights get a vivid color (at least 80 % saturation)."""
    import colorsys

    from homeassistant.util import color as color_util

    from custom_components.scene_studio.music_scenes import extract_cover_colors

    colors = extract_cover_colors(_image([(150, 100, 200), (110, 140, 190)]))  # about 35-50 % saturation
    assert colors
    for x, y in colors:
        r, g, b = color_util.color_xy_to_RGB(x, y)
        _, sat, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        assert sat >= 0.75, (x, y, sat)


def fake_lights(hass, entity_ids):
    attrs = {"supported_color_modes": ["xy", "color_temp"], "color_mode": "xy"}
    for entity_id in entity_ids:
        hass.states.async_set(entity_id, "off", attrs)

    async def turn_on(call):
        ids = call.data["entity_id"]
        for entity_id in [ids] if isinstance(ids, str) else ids:
            new = dict(hass.states.get(entity_id).attributes)
            for key in ("brightness", "xy_color", "color_temp_kelvin"):
                if key in call.data:
                    new[key] = tuple(call.data[key]) if key == "xy_color" else call.data[key]
            new["color_mode"] = "color_temp" if "color_temp_kelvin" in call.data else "xy"
            hass.states.async_set(entity_id, "on", new)

    async def turn_off(call):
        ids = call.data["entity_id"]
        for entity_id in [ids] if isinstance(ids, str) else ids:
            hass.states.async_set(entity_id, "off", dict(hass.states.get(entity_id).attributes))

    hass.services.async_register("light", "turn_on", turn_on)
    hass.services.async_register("light", "turn_off", turn_off)


def player(hass, entity_id, state, album="Album 1"):
    hass.states.async_set(entity_id, state, {
        "media_album_name": album, "media_artist": "Artist",
        "entity_picture": f"/api/media_player_proxy/{entity_id}?token=x&cache={album}",
    })


async def music_setup(hass, monkeypatch):
    import custom_components.scene_studio.music_scenes as ms

    fetched = []

    async def fake_cover(self, scene_id, state):
        fetched.append(self._album_key(state))
        self._colors[scene_id] = (self._album_key(state), COVER)
        return COVER

    monkeypatch.setattr(ms.MusicScenes, "_colors_from_cover", fake_cover)
    fake_lights(hass, LIGHTS + LIGHTS_2)
    player(hass, PLAYER, "paused")
    player(hass, PLAYER_2, "paused")
    await setup(hass, monkeypatch)
    return fetched


async def save(hass, name, lights, media_player, **music):
    r = await hass.services.async_call("scene_studio", "save_scene", {
        "name": name, "preset_id": MUSIC, "targets": {"entity_id": lights},
        "music": {"media_player": media_player, **music},
    }, blocking=True, return_response=True)
    return r["scene"]["id"]


def key(album, entity_id=PLAYER):
    return f"/api/media_player_proxy/{entity_id}|{album}"


def music(hass):
    return runtime(hass).music_scenes


def on(hass, entity_id):
    return hass.states.get(entity_id).state == "on"


async def wait(hass, seconds):
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


async def test_select_without_music_waits_for_a_cover(hass: HomeAssistant, monkeypatch, userdata):
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    assert not any(on(hass, l) for l in LIGHTS)  # no cover yet: nothing happens
    assert scene_id in music(hass).sessions
    # Music starts: the cover colors come on
    player(hass, PLAYER, "playing")
    await wait(hass, 6)
    assert fetched == [key("Album 1")]
    assert all(on(hass, l) for l in LIGHTS)


async def test_selected_without_music_is_not_restored(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    await hass.services.async_call("light", "turn_on", {"entity_id": "light.a"}, blocking=True)
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    player(hass, PLAYER, "paused")
    await wait(hass, 31)
    assert on(hass, "light.a")


async def test_music_preset_applied_directly(hass: HomeAssistant, monkeypatch, userdata):
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import entity_registry as er

    area = ar.async_get(hass).async_create("Living room")
    registry = er.async_get(hass)
    entry = registry.async_get_or_create("media_player", "sonos", "living", suggested_object_id="living_room")
    registry.async_update_entity(entry.entity_id, area_id=area.id)
    light = registry.async_get_or_create("light", "hue", "a", suggested_object_id="a")
    registry.async_update_entity(light.entity_id, area_id=area.id)
    await music_setup(hass, monkeypatch)

    await hass.services.async_call("scene_studio", "apply_preset", {
        "preset_id": MUSIC, "targets": {"entity_id": ["light.a"]}}, blocking=True)
    assert not on(hass, "light.a")  # no music: nothing happens
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "apply_preset", {
        "preset_id": MUSIC, "targets": {"entity_id": ["light.a"]}}, blocking=True)
    assert music(hass).player_in_area(area.id) == PLAYER
    assert on(hass, "light.a")


async def test_music_end_restores_state_before(hass: HomeAssistant, monkeypatch, userdata):
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    assert fetched == [key("Album 1")]
    from custom_components.scene_studio.file_utils import RUNTIME_PRESETS
    assert RUNTIME_PRESETS[f"music_{scene_id}"]["lights"] == [{"x": x, "y": y} for x, y in COVER]

    # A short pause (next track) does nothing
    player(hass, PLAYER, "paused")
    await wait(hass, 10)
    player(hass, PLAYER, "playing")
    await wait(hass, 40)
    assert scene_id in music(hass).sessions and on(hass, "light.a")

    # Music stops: after the delay the lights are off again, like before
    player(hass, PLAYER, "paused")
    await wait(hass, 31)
    assert scene_id not in music(hass).sessions
    assert not on(hass, "light.a") and not on(hass, "light.b")


async def test_auto_start_only_when_lights_off(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER, auto_start="always")
    await hass.services.async_call("light", "turn_on", {"entity_id": "light.a"}, blocking=True)
    player(hass, PLAYER, "playing")
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions  # light was on: left alone

    player(hass, PLAYER, "paused")
    await hass.services.async_call("light", "turn_off", {"entity_id": "light.a"}, blocking=True)
    player(hass, PLAYER, "playing")
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions and on(hass, "light.b")


async def test_auto_start_when_on_overrides(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER, auto_start="always", when_on=True)
    await hass.services.async_call("light", "turn_on", {"entity_id": "light.a"}, blocking=True)
    player(hass, PLAYER, "playing")
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions


async def test_follow_needs_active_music_scene(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    living = await save(hass, "Living music", LIGHTS, PLAYER)
    bedroom = await save(hass, "Bedroom music", LIGHTS_2, PLAYER_2, auto_start="follow")

    player(hass, PLAYER_2, "playing")
    await hass.async_block_till_done()
    assert bedroom not in music(hass).sessions  # nothing to follow
    player(hass, PLAYER_2, "paused")

    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": living}, blocking=True)
    await hass.async_block_till_done()
    # The music moves to the bedroom (Follow Me Music): bedroom starts, living room returns to off
    player(hass, PLAYER_2, "playing")
    player(hass, PLAYER, "paused")
    await hass.async_block_till_done()
    assert bedroom in music(hass).sessions and on(hass, "light.c")
    await wait(hass, 31)
    assert living not in music(hass).sessions and not on(hass, "light.a")


async def test_other_scene_takes_over_without_restore(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.services.async_call("scene_studio", "apply_preset", {
        "preset_id": PRESET, "targets": {"entity_id": LIGHTS}}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions
    player(hass, PLAYER, "paused")
    await wait(hass, 31)
    assert on(hass, "light.a")  # the other scene stays


async def test_lights_off_ends_music_scene(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions


async def test_new_cover_changes_colors_quickly(hass: HomeAssistant, monkeypatch, userdata):
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    # Skipping through tracks: only the cover that stays is read
    player(hass, PLAYER, "playing", album="Album 2")
    player(hass, PLAYER, "playing", album="Album 3")
    await hass.async_block_till_done()
    assert fetched == [key("Album 1")]
    await wait(hass, 6)
    assert fetched == [key("Album 1"), key("Album 3")]


async def test_new_track_same_cover_moves_colors(hass: HomeAssistant, monkeypatch, userdata):
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    calls = []
    import custom_components.scene_studio.music_scenes as ms
    original = ms.apply_preset

    async def spy(*args, **kwargs):
        calls.append(args[3])  # transition
        return await original(*args, **kwargs)

    monkeypatch.setattr(ms, "apply_preset", spy)
    hass.states.async_set(PLAYER, "playing", {**hass.states.get(PLAYER).attributes, "media_title": "Track 2"})
    await wait(hass, 6)
    assert fetched == [key("Album 1")]  # same cover, nothing to read
    assert calls == [ms.TRACK_TRANSITION]


async def test_any_speaker_follows_the_music(hass: HomeAssistant, monkeypatch, userdata):
    """Speaker "any": the scene takes the cover of whichever speaker plays, also another room's."""
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Office music", LIGHTS, "any")
    player(hass, PLAYER_2, "playing", album="Kitchen")
    await hass.async_block_till_done()
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    assert music(hass).sessions[scene_id].media_player == PLAYER_2
    assert fetched == [key("Kitchen", PLAYER_2)] and all(on(hass, l) for l in LIGHTS)

    # the kitchen stops, the living room plays: the scene follows instead of ending
    player(hass, PLAYER_2, "paused", album="Kitchen")
    player(hass, PLAYER, "playing", album="Living")
    await wait(hass, 6)
    assert music(hass).sessions[scene_id].media_player == PLAYER
    assert key("Living") in fetched

    # all music off: after the delay the scene ends and the lights go back to off
    player(hass, PLAYER, "paused", album="Living")
    await wait(hass, 31)
    assert scene_id not in music(hass).sessions
    assert not any(on(hass, l) for l in LIGHTS)


async def test_saturation_of_a_scene(hass: HomeAssistant, monkeypatch, userdata):
    """Color intensity: more vivid or paler colors of the preset, hue unchanged, whites untouched."""
    import colorsys

    from homeassistant.util import color as color_util

    from custom_components.scene_studio.color_management import adjust_saturation

    def sat(xy):
        r, g, b = color_util.color_xy_to_RGB(*xy)
        return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    pale = color_util.color_RGB_to_xy(200, 150, 230)
    white = color_util.color_RGB_to_xy(255, 245, 240)
    vivid, white_after = adjust_saturation([pale, white], 100)
    assert sat(vivid)[1] > 0.95 and abs(sat(vivid)[0] - sat(pale)[0]) < 0.03
    assert white_after == white
    paler = adjust_saturation([pale], -50)[0]
    assert sat(paler)[1] < sat(pale)[1] * 0.6
    assert adjust_saturation([pale], 0) == [pale] and adjust_saturation([pale], None) == [pale]

    # a saved scene passes it on to the lights
    fake_lights(hass, ["light.x"])
    await setup(hass, monkeypatch)
    r = await hass.services.async_call("scene_studio", "save_scene", {
        "name": "Vivid", "preset_id": PRESET, "targets": {"entity_id": ["light.x"]}, "saturation": 100,
    }, blocking=True, return_response=True)
    assert r["scene"]["saturation"] == 100
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": r["scene"]["id"]}, blocking=True)
    await hass.async_block_till_done()
    assert sat(hass.states.get("light.x").attributes["xy_color"])[1] > 0.9


async def test_lights_back_on_continue_with_the_current_cover(hass: HomeAssistant, monkeypatch, userdata):
    """Option resume: a motion light turns the lights off and later on again (plain light.turn_on):
    while the music still plays, the music scene continues with the cover playing now."""
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Kitchen music", LIGHTS, PLAYER, resume=True)
    player(hass, PLAYER, "playing", album="Album 1")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    assert all(on(hass, l) for l in LIGHTS)

    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions

    player(hass, PLAYER, "playing", album="Album 2")  # the cover changed meanwhile
    await wait(hass, 60)
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions
    assert fetched[-1] == key("Album 2")


async def test_lights_back_on_without_music_or_other_scene(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Kitchen music", LIGHTS, PLAYER, resume=True)
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()

    # another scene on these lights: the music scene does not come back
    await hass.services.async_call("scene_studio", "apply_preset", {
        "preset_id": PRESET, "targets": {"entity_id": LIGHTS}}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions and not music(hass)._sleeping

    # music stopped: lights turned on stay as they are
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    player(hass, PLAYER, "paused")
    await hass.async_block_till_done()
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions


async def test_any_speaker_ignores_tv_sound(hass: HomeAssistant, monkeypatch, userdata):
    """A Sonos playing TV sound (no cover) does not count for "any speaker"."""
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Office music", LIGHTS, "any")
    player(hass, PLAYER, "playing", album="Kitchen")
    await hass.async_block_till_done()
    hass.states.async_set(PLAYER_2, "playing", {"source": "TV", "media_title": "TV"})  # started later
    await hass.async_block_till_done()
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()
    assert music(hass).sessions[scene_id].media_player == PLAYER
    assert fetched == [key("Kitchen")]


async def activate(hass, scene_id):
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    await hass.async_block_till_done()


async def test_lights_back_on_stay_plain_light_by_default(hass: HomeAssistant, monkeypatch, userdata):
    """Without the option resume a music scene is over once its lights were off: lights turned on
    again (by hand or by a motion light) are normal light, also while the music still plays."""
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Kitchen music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await activate(hass, scene_id)
    await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions and not music(hass)._sleeping

    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHTS}, blocking=True)
    player(hass, PLAYER, "playing", album="Album 2")
    await wait(hass, 6)
    assert scene_id not in music(hass).sessions
    assert fetched == [key("Album 1")]


@pytest.mark.parametrize(("service", "data"), [
    ("stop_all_dynamic_scenes", {}),
    ("stop_dynamic_scenes_for_targets", {"targets": {"entity_id": LIGHTS}}),
])
async def test_stop_services_end_the_music_scene(hass: HomeAssistant, monkeypatch, userdata, service, data):
    """Stop means stop: the next cover does not bring the colors back."""
    fetched = await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await activate(hass, scene_id)
    assert scene_id in music(hass).sessions

    await hass.services.async_call("scene_studio", service, data, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions
    assert all(on(hass, light) for light in LIGHTS)  # the lights stay as they are

    player(hass, PLAYER, "playing", album="Album 2")
    await wait(hass, 6)
    assert scene_id not in music(hass).sessions
    assert fetched == [key("Album 1")]


async def test_stopping_the_color_loop_ends_the_music_scene(hass: HomeAssistant, monkeypatch, userdata):
    """The stop button of the panel stops the running dynamic scene by its id."""
    fetched = await music_setup(hass, monkeypatch)
    r = await hass.services.async_call("scene_studio", "save_scene", {
        "name": "Living music", "preset_id": MUSIC, "targets": {"entity_id": LIGHTS}, "dynamic": True,
        "interval": 60, "music": {"media_player": PLAYER},
    }, blocking=True, return_response=True)
    scene_id = r["scene"]["id"]
    player(hass, PLAYER, "playing")
    # no async_block_till_done while the color loop runs: it would wait for the loop to end
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    running = runtime(hass).dynamic_scenes.get_all()
    assert len(running) == 1 and scene_id in music(hass).sessions

    await hass.services.async_call("scene_studio", "stop_dynamic_scene", {"id": running[0].id}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions

    player(hass, PLAYER, "playing", album="Album 2")
    await wait(hass, 6)
    assert not runtime(hass).dynamic_scenes.get_all()
    assert fetched == [key("Album 1")]


async def test_scene_of_home_assistant_ends_the_music_scene_dimming_does_not(
    hass: HomeAssistant, monkeypatch, userdata
):
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    player(hass, PLAYER, "playing")
    await activate(hass, scene_id)

    # dimming or changing a light by hand: the music scene goes on
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHTS, "brightness": 40}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions

    # a scene on other lights: no effect
    hass.states.async_set("scene.elsewhere", "unknown", {"entity_id": LIGHTS_2})
    hass.bus.async_fire("call_service", {
        "domain": "scene", "service": "turn_on", "service_data": {"entity_id": "scene.elsewhere"}})
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions

    # a scene of Home Assistant on these lights: the music scene ends
    hass.states.async_set("scene.white", "unknown", {"entity_id": LIGHTS})
    hass.bus.async_fire("call_service", {
        "domain": "scene", "service": "turn_on", "service_data": {"entity_id": ["scene.white"]}})
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions

    # scene.apply names the lights itself
    await activate(hass, scene_id)
    assert scene_id in music(hass).sessions
    hass.bus.async_fire("call_service", {
        "domain": "scene", "service": "apply", "service_data": {"entities": {"light.a": {"state": "on"}}}})
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions


async def test_selecting_a_music_scene_entity_does_not_end_it(hass: HomeAssistant, monkeypatch, userdata):
    """scene.turn_on of the music scene itself starts it; it must not count as another scene."""
    from homeassistant.helpers import entity_registry as er

    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id("scene", "scene_studio", f"saved_scene_{scene_id}")
    assert entity_id
    player(hass, PLAYER, "playing")
    await activate(hass, scene_id)
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions


async def test_gap_between_tracks_is_not_a_music_start(hass: HomeAssistant, monkeypatch, userdata):
    """Auto start "always": a stopped music scene stays stopped while the music goes on, also when the
    player leaves "playing" for a moment between two tracks. After a real break it starts again."""
    await music_setup(hass, monkeypatch)
    scene_id = await save(hass, "Living music", LIGHTS, PLAYER, auto_start="always", when_on=True)
    player(hass, PLAYER, "playing")
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions

    await hass.services.async_call("scene_studio", "stop_all_dynamic_scenes", {}, blocking=True)
    assert scene_id not in music(hass).sessions

    player(hass, PLAYER, "idle", album="Album 2")
    player(hass, PLAYER, "playing", album="Album 2")
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions

    player(hass, PLAYER, "paused", album="Album 2")
    await hass.async_block_till_done()
    music(hass)._stopped_at[PLAYER] -= 31  # the music was off for more than 30 s
    player(hass, PLAYER, "playing", album="Album 3")
    await hass.async_block_till_done()
    assert scene_id in music(hass).sessions


@pytest.mark.parametrize("ended_by", ["scene", "lights_off"])
async def test_ended_music_scene_stops_its_color_loop(hass: HomeAssistant, monkeypatch, userdata, ended_by):
    """A scene of Home Assistant or turning the lights off ends a dynamic music scene completely: its
    color loop does not change the lights of the new scene and does not come back with the lights."""
    import asyncio

    await music_setup(hass, monkeypatch)
    r = await hass.services.async_call("scene_studio", "save_scene", {
        "name": "Living music", "preset_id": MUSIC, "targets": {"entity_id": LIGHTS}, "dynamic": True,
        "interval": 60, "music": {"media_player": PLAYER},
    }, blocking=True, return_response=True)
    scene_id = r["scene"]["id"]
    player(hass, PLAYER, "playing")
    await hass.services.async_call("scene_studio", "activate_saved_scene", {"id": scene_id}, blocking=True)
    assert len(runtime(hass).dynamic_scenes.get_all()) == 1
    for _ in range(20):  # let the color loop turn the lights on
        await asyncio.sleep(0)
    assert all(on(hass, light) for light in LIGHTS)

    if ended_by == "scene":
        hass.bus.async_fire("call_service", {
            "domain": "scene", "service": "apply", "service_data": {"entities": {"light.a": {"state": "on"}}}})
    else:
        await hass.services.async_call("light", "turn_off", {"entity_id": LIGHTS}, blocking=True)
    for _ in range(5):
        await asyncio.sleep(0)
    assert not runtime(hass).dynamic_scenes.get_all()
    await hass.async_block_till_done()
    assert scene_id not in music(hass).sessions


def _sky_cover():
    """A cover like the one of issue 13: three quarters pale blue sky, a small vivid red part, some black."""
    image = Image.new("RGB", (96, 96), (222, 229, 250))  # pale blue
    for x in range(96):
        for y in range(96):
            if y >= 84:
                image.putpixel((x, y), (20, 18, 16))  # dark
            elif 36 <= x < 60 and 30 <= y < 84:
                image.putpixel((x, y), (215, 45, 50))  # vivid red, 14 % of the picture
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _hue_sat(xy):
    import colorsys

    from homeassistant.util import color as color_util

    r, g, b = color_util.color_xy_to_RGB(*xy)
    h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s


def test_color_choice_from_vivid_to_area():
    from custom_components.scene_studio.music_scenes import extract_cover_colors, extract_cover_palette

    cover = _sky_cover()
    # vivid (default, as before 3.6): the small red part wins, the pale sky is ignored
    vivid = extract_cover_palette(cover)
    assert vivid["colors"] == extract_cover_colors(cover)
    hue, sat = _hue_sat(vivid["main"][0])
    assert (hue < 15 or hue > 345) and sat > 0.8
    assert all(not 200 < _hue_sat(c)[0] < 250 for c in vivid["colors"])

    # area: the sky is the main color and stays a light blue, red is the accent
    area = extract_cover_palette(cover, 0)
    hue, sat = _hue_sat(area["main"][0])
    assert 200 < hue < 250 and sat < 0.6
    assert all(200 < _hue_sat(c)[0] < 260 for c in area["main"])
    accent_hue = _hue_sat(area["accent"][0])[0]
    assert accent_hue < 15 or accent_hue > 345

    # one color only: the accents are variants of it, not the same color
    single = extract_cover_palette(_image([(255, 0, 0)]))
    assert single["accent"] and single["main"][0] not in single["accent"]


@pytest.mark.parametrize("dynamic", [False, True])
async def test_main_and_accent_lights(hass: HomeAssistant, monkeypatch, userdata, dynamic):
    """Lights with a role take only the main or only the accent colors, the others all colors."""
    import asyncio

    import custom_components.scene_studio.music_scenes as ms

    main, accent = [(0.15, 0.06), (0.16, 0.08)], [(0.64, 0.33), (0.3, 0.6)]
    await music_setup(hass, monkeypatch)

    async def fake_cover(self, scene_id, state):
        self._colors[scene_id] = (self._album_key(state), main[:1] + accent)
        self._pools[scene_id] = {"main": main, "accent": accent, "focus": 0}
        return main[:1] + accent

    monkeypatch.setattr(ms.MusicScenes, "_colors_from_cover", fake_cover)
    lights = LIGHTS + LIGHTS_2
    r = await hass.services.async_call("scene_studio", "save_scene", {
        "name": "Living music", "preset_id": MUSIC, "targets": {"entity_id": lights}, "dynamic": dynamic,
        "interval": 60,
        "music": {"media_player": PLAYER, "focus": 0, "roles": {lights[0]: "main", lights[1]: "accent"}},
    }, blocking=True, return_response=True)
    assert r["scene"]["music"]["roles"] == {lights[0]: "main", lights[1]: "accent"}
    assert r["scene"]["music"]["focus"] == 0
    player(hass, PLAYER, "playing")
    for _ in range(8):  # shuffled: the roles must hold every time
        await hass.services.async_call(
            "scene_studio", "activate_saved_scene", {"id": r["scene"]["id"]}, blocking=True)
        for _ in range(20):
            await asyncio.sleep(0)
        assert hass.states.get(lights[0]).attributes["xy_color"] in main
        assert hass.states.get(lights[1]).attributes["xy_color"] in accent
        assert hass.states.get(lights[2]).attributes["xy_color"] in main[:1] + accent
    await hass.services.async_call("scene_studio", "stop_all_dynamic_scenes", {}, blocking=True)
    await hass.async_block_till_done()


async def test_scenes_without_roles_are_saved_with_the_defaults(hass: HomeAssistant, monkeypatch, userdata):
    await music_setup(hass, monkeypatch)
    r = await hass.services.async_call("scene_studio", "save_scene", {
        "name": "Living music", "preset_id": MUSIC, "targets": {"entity_id": LIGHTS}, "music": {"media_player": PLAYER},
    }, blocking=True, return_response=True)
    assert r["scene"]["music"]["focus"] == 100 and r["scene"]["music"]["roles"] == {}
