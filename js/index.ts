// Modified for MB Scene Creator (2026): independent integration namespace.
import MBSceneCreatorPanel from "./MBSceneCreatorPanel";

const ELEMENT_NAME = "mb-scene-creator-panel";

if (!window.customElements.get(ELEMENT_NAME)) {
    window.customElements.define(ELEMENT_NAME, MBSceneCreatorPanel);
}
