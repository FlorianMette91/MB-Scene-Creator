"""The personal integration must not register the original integration's identifiers."""
import json
from pathlib import Path


def test_independent_namespace():
    root = Path(__file__).resolve().parents[1]
    component = root / 'custom_components' / 'mb_scene_creator'
    from custom_components.mb_scene_creator.const import DOMAIN, PANEL_URL, ROOM_CARD_URL
    from custom_components.mb_scene_creator.saved_scenes import STORAGE_KEY
    assert DOMAIN == 'mb_scene_creator'
    assert 'mb_scene_creator' in PANEL_URL and 'mb_scene_creator' in ROOM_CARD_URL
    assert STORAGE_KEY == 'mb_scene_creator.saved_scenes'
    assert json.loads((component / 'manifest.json').read_text())['domain'] == DOMAIN
    for base in (component, root / 'js'):
        for path in base.rglob('*'):
            if path.suffix not in {'.py', '.ts', '.tsx', '.js', '.json'}:
                continue
            text = path.read_text()
            assert 'scene_studio' not in text, str(path)
            assert 'scene-studio' not in text, str(path)
