# Coming from Scene Presets

MB Scene Creator started as a further development of
[Scene Presets](https://github.com/Hypfer/hass-scene_presets). It is a **separate integration**
(domain `mb_scene_creator`): both can be installed at the same time, they do not share services,
storage, panel or cards.

## Import

<img src="../img/import.png" width="360" alt="Scene Presets found">

When MB Scene Creator finds data of Scene Presets, the panel shows **Scene Presets found** on top
(for admins). **Import** brings over:

- **Saved scenes** (from forks of Scene Presets that have them) with all settings and their IDs
- **Own presets** and replaced pictures of built-in presets (`userdata/custom`)
- with **Keep the scene entities** (default): the scene entities of the saved scenes with the same
  **entity ID, name, icon, area and labels**, so dashboards, automations and voice assistants keep
  working. Scene Presets is **disabled** for that (not removed), otherwise it would create its
  scene entities again.

Favorites, the chosen lights and the settings of the panel are taken over in each browser the first
time MB Scene Creator is opened there.

The same import is available as a service (admins only, like the button in the panel):

```yaml
action: mb_scene_creator.import_scene_presets
data:
  take_over_entities: true   # default
  overwrite: false           # import scenes and files again that exist already
```

Scenes that were imported before are skipped, so the import can be repeated safely.

## After the import

| Used with Scene Presets | With MB Scene Creator |
|---|---|
| `scene_presets.apply_preset`, `start_dynamic_scene`, … | `mb_scene_creator.apply_preset`, `start_dynamic_scene`, … (same fields) |
| `type: custom:scene-presets-room-card` | `type: custom:mb-scene-creator-room-card` (same options) |
| Panel *Scene Presets* | Panel *MB Scene Creator* |
| `scene.*` entities of saved scenes | the same entities (if taken over) |
| Preset IDs | unchanged |

When everything works, remove Scene Presets under **Settings → Devices & services** and in HACS.
Until then you can go back: delete the imported scenes in MB Scene Creator, then enable Scene Presets
again (the areas of its scene entities have to be set again).
