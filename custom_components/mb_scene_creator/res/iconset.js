// Modified by Codex (2026): original MB monogram and three light points.
// Modified for MB Scene Creator (2026): independent integration namespace.
// Adapted from from https://github.com/hacs/integration/blob/7d46a52de0df2466aa65e446458b952150398f4c/custom_components/hacs/iconset.js
const mbSceneCreatorIcons = {
    mb_scene_creator: {
        path: "M2 8H4L7 12.5 10 8H12V21H9.5V12.5L7 16.3 4.5 12.5V21H2ZM14 8H18.3C22.7 8 23 12.3 20.5 14C24 15.4 23 21 18.5 21H14ZM16.5 10.5V13H18C20 13 20 10.5 18 10.5ZM16.5 15.5V18.5H18.4C20.8 18.5 20.8 15.5 18.4 15.5ZM5.5 4a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0ZM10.5 4a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0ZM15.5 4a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0Z",
        keywords: ["mb_scene_creator"],
    },
};

window.customIcons = window.customIcons || {};
window.customIconsets = window.customIconsets || {};

window.customIcons["mb_scene_creator"] = {
    getIcon: async (iconName) => (
        {path: mbSceneCreatorIcons[iconName]?.path}
    ),
    getIconList: async () =>
        Object.entries(mbSceneCreatorIcons).map(([icon, content]) => ({
                name: icon,
                keywords: content.keywords,
            })
        )
};