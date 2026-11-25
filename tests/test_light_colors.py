# Modified for MB Scene Creator (2026): independent integration namespace.
"""Per-light colors survive saving and override a palette without changing other lamps."""

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from .test_custom_presets import setup, userdata  # noqa: F401
from .test_color_modes import PRESET


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_save_activate_and_reset_color(hass: HomeAssistant, monkeypatch, userdata):
    calls = []

    async def turn_on(call):
        calls.append(dict(call.data))

    hass.services.async_register("light", "turn_on", turn_on)
    for name in ("custom", "preset"):
        hass.states.async_set(f"light.{name}", "on", {"supported_color_modes": ["xy"]})
    await setup(hass, monkeypatch)
    payload = {
        "id": "own-colors", "name": "Own colors", "preset_id": PRESET,
        "targets": {"entity_id": ["light.custom", "light.preset"]},
        "light_colors": {"light.custom": [0.65, 0.3]},
        "light_brightness": {"light.custom": 25}, "saturation": -100,
    }
    await hass.services.async_call("mb_scene_creator", "save_scene", payload, blocking=True)
    await hass.services.async_call("mb_scene_creator", "activate_saved_scene", {"id": "own-colors"}, blocking=True)
    await hass.async_block_till_done()
    got = {c["entity_id"]: c for c in calls}
    assert tuple(got["light.custom"]["xy_color"]) == (0.65, 0.3)
    assert got["light.custom"]["brightness"] == round(255 * .25)
    assert tuple(got["light.preset"]["xy_color"]) != (0.65, 0.3)
    calls.clear()
    del payload["light_colors"]
    await hass.services.async_call("mb_scene_creator", "save_scene", payload, blocking=True)
    await hass.services.async_call("mb_scene_creator", "activate_saved_scene", {"id": "own-colors"}, blocking=True)
    await hass.async_block_till_done()
    assert all(tuple(c["xy_color"]) != (0.65, 0.3) for c in calls)


@pytest.mark.parametrize("color", [[-1, .3], [.5, 0], [.5, 2], [.2], [.2, .3, .4], [float("nan"), .3]])
def test_invalid_colors_rejected(color):
    from custom_components.mb_scene_creator import LIGHT_COLORS
    with pytest.raises(vol.Invalid):
        LIGHT_COLORS({"light.test": color})
