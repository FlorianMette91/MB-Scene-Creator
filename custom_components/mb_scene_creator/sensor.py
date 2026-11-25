# Modified for MB Scene Creator (2026): independent integration namespace.
"""The time of day as MB Scene Creator sees it (day, dusk, night), see daytime.py.

Other integrations and automations can use it, so the whole home shares one definition of night.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .daytime import PHASES, Daytime
from .data import MBSceneCreatorConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: MBSceneCreatorConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([DaytimeSensor(entry.runtime_data.daytime)])


class DaytimeSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_name = "MB Scene Creator time of day"
    _attr_translation_key = "daytime"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(PHASES)
    _attr_unique_id = "mb_scene_creator_daytime"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(self, daytime: Daytime):
        self._daytime = daytime

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._daytime.add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> str:
        return self._daytime.phase

    @property
    def extra_state_attributes(self) -> dict:
        # when each phase begins next
        return {f"next_{phase}": when.isoformat() for phase, when in reversed(self._daytime.changes(4))}
