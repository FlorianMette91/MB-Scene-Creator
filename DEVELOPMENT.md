# Development

Owner: FlorianMette91. Integration domain: `mb_scene_creator`.
Upstream: https://github.com/andrejem/scene-studio
Initial baseline: 3.7.1, commit `9b8ded1a71cae18901b9ac0392bb6710aa8604f1`.
Original copyright notices, LICENSE, NOTICE and asset credits must be preserved.

## Working on a feature

Create a feature branch, change the Python integration and/or React panel, then open a pull request.
Keep every service/storage/browser namespace independent of Scene Studio.
Never copy user credentials or Home Assistant's `.storage` directory into this repository.

```sh
npm ci
npm run build
python3.13 -m venv .venv
.venv/bin/pip install pytest-homeassistant-custom-component==0.13.316
.venv/bin/pytest -q
```

Commit the generated `custom_components/mb_scene_creator/frontend/mb_scene_creator_panel.js`.
The pinned test dependency currently uses Home Assistant 2026.2.3; the declared runtime minimum
is 2026.7. Testing a current Home Assistant installation remains necessary before relying on a release.

## Releases

After merging the pull request, set the desired version in
`custom_components/mb_scene_creator/manifest.json` and create a GitHub release with
matching tag `vVERSION`. For a public repository, Marketplace uses the integration directory in that tag; no separate
upload is required. Build the panel before tagging. Do not edit published tags.

## Initial personal changes

- Fully independent `mb_scene_creator` namespace, panel, card and persistent data.
- Optional per-light CIE xy colors, including independent hue and saturation editing.
- Color persistence and propagation through static, dynamic, optional and music paths.
- Explicit colors override scene saturation, shuffle and gradients.
- Original Scene Studio data is not imported automatically.

Use upstream as a read-only reference. Port upstream fixes on a feature branch and review
namespace changes rather than overwriting this integration with the upstream files.
