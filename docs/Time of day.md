# Time of day scenes

A time of day scene has no colors of its own. It stands for **another saved scene, depending on
whether it is day, dusk or night**. One button, one automation or one tile in the room card then
always starts the fitting scene: bright during the day, dimmed in the evening, a night light at night.

## In short

- Three times of day: **day**, **dusk** and **night**. When they begin is set **once** for all
  time of day scenes – by the sun, by the clock, or both.
- A time of day scene is a normal saved scene with its own scene entity. Wherever a scene can be
  started, it can be used.
- Optionally the scene **changes with the time of day** while the lights are on.
- The current time of day is also available as the sensor `sensor.scene_studio_time_of_day`
  (`day`, `dusk`, `night`), for your own automations.

## Setting it up

1. Save the scenes you want to use (e.g. *Bright*, *Dimmed*, *Night light*).
2. Tab **Presets** → tap the preset **Time of day** (category *Basics*). Or in a new scene, choose
   the preset **Time of day**.
3. Give it a name and a room, and choose a scene for **Day**, **Dusk** and **Night**. Scenes of the
   chosen room are listed first.
4. Save.

A time of day without a scene uses the scene of the time before it: night → dusk → day,
dusk → day. So a scene for the day alone is enough to start with.

## When day, dusk and night begin

The clock button at the top of the editor opens **Times of day** (admins). It applies to the whole
integration, not to one scene.

Each of the three limits – *dusk begins*, *night begins*, *day begins* – has three fields:

| Field | Meaning |
|---|---|
| **Sun below / above** | The limit is reached when the sun passes this elevation (0° = sunrise or sunset, −6° = end of civil twilight, −18° = fully dark) |
| **Not before** | Even if the sun is already there, the phase does not begin before this time |
| **At the latest** | Even if the sun is not there yet (or never gets there), the phase begins at this time |

Leave a field empty to not use it. A limit with only times is a plain clock time.

This is what makes one setting work all year. Example for *night begins*: sun below −25°,
not before 22:00, at the latest 23:30.

| | Without times | With times |
|---|---|---|
| **Winter** | Night from about 19:15, long before bedtime | Night from 22:00 |
| **Summer** | Never night: in Central Europe the sun does not get that low | Night from 23:30 |

Below the fields the panel shows what the settings give right now: the current time of day and when
the next ones begin. It updates while you type, nothing is saved until you press **Save**.

In the morning the same applies the other way round: night lasts until the sun rises above the
night elevation again (then it is dusk) or until the day begins.

## Change with the time of day

Off by default: the scene of the moment is started once and stays until you start another one.

With **Change with the time of day** the scene keeps watching. When the next time of day begins
while its lights are on, it changes to the scene of that time, slowly (30 seconds). This ends when

- another scene is started on these lights (Scene Studio or a scene of Home Assistant),
- you stop it (`stop_dynamic_scenes_for_targets`, `stop_all_dynamic_scenes`, the stop button),
- or all of its lights are turned off.

Dimming a light or changing its color by hand does not end it; the next change of the time of day
applies the new scene.

## One lamp only

Like every saved scene, a time of day scene can be applied to other lights
([lamp modes](Lamp%20modes.md)): `activate_saved_scene` with `targets`. A button on the bedside
table can so turn on only its lamp, in the scene of the current time of day.

```yaml
action: scene_studio.activate_saved_scene
data:
  id: 1b2c3d4e-0000-0000-0000-000000000000
  targets:
    entity_id: light.bedside_left
```

## Services

`save_scene` with the preset *Time of day* (`d4a1f7c0-6b3e-4e52-8c1d-2f9a7b5e0c63`) and the field
`daytime`:

```yaml
action: scene_studio.save_scene
data:
  name: Living room automatic
  preset_id: d4a1f7c0-6b3e-4e52-8c1d-2f9a7b5e0c63
  targets:
    area_id: living_room
  daytime:
    day: <id of a saved scene>
    dusk: <id of a saved scene>
    night: <id of a saved scene>
    follow: false
```

The preset cannot be applied directly (`apply_preset`, `start_dynamic_scene`): it has no colors.
