// Added by andrejem (2026): time of day scenes (3.7) - a scene that stands for another saved scene per
// phase (day, dusk, night), and the settings when these phases begin (sun elevation and clock times).

import React, {useEffect, useRef, useState} from "react";
import HaIcon from "./hass/building_blocks/HaIcon";
import {SwitchRow} from "./Controls";
import {Key, Translate} from "../i18n";
import {
    DAYTIME_PRESET_ID, DaytimeConfig, DaytimePhase, DaytimeState, PHASES, SavedScene, areaName, newId, sceneAreaId, sceneEntityId, stripRoomName
} from "../tunables";
import {SceneDraft} from "./SceneEditor";

const PHASE_ICON: {[phase: string]: string} = {day: "mdi:white-balance-sunny", dusk: "mdi:weather-sunset", night: "mdi:weather-night"};
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// times are shown in the time zone of Home Assistant, not of the browser
const clock = (hass: any, iso: string): string => {
    const timeZone = hass?.config?.time_zone;
    const date = new Date(iso);
    const time = date.toLocaleTimeString(hass?.locale?.language ?? undefined, {hour: "2-digit", minute: "2-digit", timeZone});
    const day = (d: Date) => d.toLocaleDateString("en-CA", {timeZone});
    return day(date) !== day(new Date()) ? time + " +1" : time;
};

/** When the next phases begin, e.g. "Dusk 16:49 · Night 22:00 · Day 07:41". */
const Upcoming: React.FunctionComponent<{hass: any, t: Translate, state: DaytimeState | null}> = ({hass, t, state}) => {
    if (!state) {
        return null;
    }
    return (
        <div className={"sp-daytime-next"}>
            <span className={"sp-daytime-now"}>
                <HaIcon icon={PHASE_ICON[state.phase]} size={18}/>
                {t("daytime_now", {phase: t(("daytime_" + state.phase) as Key)})}
            </span>
            {state.next.map(n => (
                <span key={n.phase + n.at} className={"sp-secondary"}>
                    <HaIcon icon={PHASE_ICON[n.phase]} size={16}/>
                    {clock(hass, n.at)}
                </span>
            ))}
        </div>
    );
};

/** Settings of the integration: when dusk, night and day begin. */
export const DaytimeSettings: React.FunctionComponent<{
    hass: any,
    t: Translate,
    state: DaytimeState,
    onClose: () => void,
    onSaved: (state: DaytimeState) => void
}> = ({hass, t, state, onClose, onSaved}) => {
    const [config, setConfig] = useState<DaytimeConfig>(state.config);
    const [preview, setPreview] = useState<DaytimeState>(state);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const timer = useRef<number | undefined>(undefined);

    // what the limits give right now, without saving
    useEffect(() => {
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => {
            hass.callWS({type: "scene_studio/preview_daytime", config}).then((result: DaytimeState) => {
                setPreview({...result, following: []});
            }).catch(() => {/* shown when saving */});
        }, 300);
        return () => window.clearTimeout(timer.current);
    }, [config]); // eslint-disable-line react-hooks/exhaustive-deps

    const setRule = (key: DaytimePhase, change: any) => setConfig(prev => ({...prev, [key]: {...prev[key], ...change}}));
    const valid = PHASES.every(key => config[key].elevation !== null || config[key].earliest || config[key].latest);

    const save = () => {
        setBusy(true);
        hass.callWS({type: "scene_studio/set_daytime", config}).then((result: DaytimeState) => {
            onSaved(result);
            onClose();
        }).catch(err => setError(err?.message ?? String(err))).finally(() => setBusy(false));
    };

    // the order of a day: dusk, night, then the next morning
    const rows: Array<DaytimePhase> = ["dusk", "night", "day"];

    return (
        <div className={"sp-overlay"} onClick={(e) => {
            if (e.target === e.currentTarget) {
                onClose();
            }
        }}>
            <div className={"sp-sheet sp-daytime-settings"} role={"dialog"} aria-modal={"true"} aria-label={t("daytime_settings")}>
                <div className={"sp-sheet-head"}>
                    <button className={"sp-icon-btn"} aria-label={t("close")} onClick={onClose}>
                        <HaIcon icon={"mdi:close"} size={24}/>
                    </button>
                    <div className={"sp-sheet-title"}>{t("daytime_settings")}</div>
                </div>
                <div className={"sp-sheet-body"}>
                    <div className={"sp-secondary sp-small"}>{t("daytime_settings_help")}</div>
                    {rows.map(key => {
                        const rule = config[key];
                        const bySun = rule.elevation !== null;
                        return (
                            <div key={key} className={"sp-daytime-rule daytime-rule-" + key}>
                                <div className={"sp-daytime-rule-head"}>
                                    <HaIcon icon={PHASE_ICON[key]} size={20}/>
                                    <span className={"sp-strong"}>{t(("daytime_begins_" + key) as Key)}</span>
                                </div>
                                <div className={"sp-daytime-rule-fields"}>
                                    <label className={"sp-field"}>
                                        <span className={"sp-field-label"}>{t(key === "day" ? "daytime_sun_above" : "daytime_sun_below")}</span>
                                        <span className={"sp-daytime-sun"}>
                                            <input
                                                type={"number"}
                                                className={"sp-input daytime-elevation"}
                                                min={-60}
                                                max={60}
                                                step={1}
                                                placeholder={"–"}
                                                value={bySun ? String(rule.elevation) : ""}
                                                onChange={(e) => setRule(key, {elevation: e.target.value === "" ? null : Number(e.target.value)})}
                                            />
                                            <span className={"sp-secondary"}>°</span>
                                        </span>
                                    </label>
                                    <label className={"sp-field"}>
                                        <span className={"sp-field-label"}>{t("daytime_earliest")}</span>
                                        <input
                                            type={"time"}
                                            className={"sp-input daytime-earliest"}
                                            value={rule.earliest ?? ""}
                                            onChange={(e) => setRule(key, {earliest: e.target.value || null})}
                                        />
                                    </label>
                                    <label className={"sp-field"}>
                                        <span className={"sp-field-label"}>{t("daytime_latest")}</span>
                                        <input
                                            type={"time"}
                                            className={"sp-input daytime-latest"}
                                            value={rule.latest ?? ""}
                                            onChange={(e) => setRule(key, {latest: e.target.value || null})}
                                        />
                                    </label>
                                </div>
                            </div>
                        );
                    })}
                    <div className={"sp-field"}>
                        <span className={"sp-field-label"}>{t("daytime_result")}</span>
                        <Upcoming hass={hass} t={t} state={preview}/>
                    </div>
                    {!valid && <div className={"sp-error"}>{t("daytime_rule_empty")}</div>}
                    {error && <div className={"sp-error"}>{error}</div>}
                </div>
                <div className={"sp-sheet-foot"}>
                    <span className={"sp-grow"}/>
                    <button className={"sp-btn primary daytime-settings-save"} disabled={!valid || busy} onClick={save}>{t("save")}</button>
                </div>
            </div>
        </div>
    );
};

/** Editor of a time of day scene: name, room, one scene per phase. */
export const DaytimeEditor: React.FunctionComponent<{
    hass: any,
    t: Translate,
    draft: SceneDraft | null,
    savedScenes: Array<SavedScene>,
    onClose: () => void,
    onSaved: () => void
}> = ({hass, t, draft, savedScenes, onClose, onSaved}) => {
    const hassRef = useRef(hass);
    hassRef.current = hass;
    const isAdmin = !!hass?.user?.is_admin;

    const [name, setName] = useState("");
    const [areaId, setAreaId] = useState<string | undefined>(undefined);
    const [scenes, setScenes] = useState<{[phase: string]: string}>({});
    const [follow, setFollow] = useState(false);
    const [state, setState] = useState<DaytimeState | null>(null);
    const [settings, setSettings] = useState(false);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    const open = draft !== null;
    const editing = draft?.scene;

    useEffect(() => {
        if (!draft) {
            return;
        }
        const saved = draft.scene?.daytime ?? {};
        setName(draft.name);
        setAreaId(draft.areaId);
        setScenes({day: saved.day ?? "", dusk: saved.dusk ?? "", night: saved.night ?? ""});
        setFollow(!!saved.follow);
        setSettings(false);
        setError("");
        hass.callWS({type: "scene_studio/get_daytime"}).then(setState).catch(() => setState(null));
    }, [draft]); // eslint-disable-line react-hooks/exhaustive-deps

    if (!open) {
        return null;
    }

    const areas = Object.values(hass?.areas ?? {}).map((a: any) => ({id: a.area_id, name: a.name}))
        .sort((a, b) => a.name.localeCompare(b.name));
    // scenes of the room first, then all others; a time of day scene cannot stand for another one
    const choices = savedScenes.filter(s => s.preset_id !== DAYTIME_PRESET_ID && s.id !== editing?.id).map(s => {
        const room = sceneAreaId(hass, s);
        return {id: s.id, room, name: s.name, label: room ? stripRoomName(s.name, areaName(hass, room)) : s.name};
    });
    const inRoom = choices.filter(c => areaId && c.room === areaId);
    const others = choices.filter(c => !(areaId && c.room === areaId));
    const chosen = PHASES.filter(p => scenes[p] && choices.some(c => c.id === scenes[p]));
    const canSave = !!name.trim() && chosen.length > 0 && !busy;
    const entityId = editing ? sceneEntityId(hass, editing.id) : undefined;

    const assignArea = async (sceneId: string) => {
        if (!isAdmin) {
            return;
        }
        for (let i = 0; i < 20; i++) {
            const id = sceneEntityId(hassRef.current, sceneId);
            if (id) {
                const current = hassRef.current?.entities?.[id]?.area_id ?? undefined;
                if (current !== areaId) {
                    await hassRef.current.callWS({type: "config/entity_registry/update", entity_id: id, area_id: areaId ?? null});
                }
                return;
            }
            await sleep(250);
        }
    };

    const save = async () => {
        const sceneId = editing ? editing.id : newId();
        const daytime: any = {follow};
        chosen.forEach(p => {
            daytime[p] = scenes[p];
        });
        setBusy(true);
        setError("");
        try {
            await hass.callService("scene_studio", "save_scene", {
                id: sceneId,
                name: name.trim(),
                preset_id: DAYTIME_PRESET_ID,
                targets: areaId ? {area_id: [areaId]} : {},
                daytime
            });
            await assignArea(sceneId);
            onSaved();
            onClose();
        } catch (err: any) {
            setError(err?.message ?? String(err));
        } finally {
            setBusy(false);
        }
    };

    const remove = () => {
        if (!editing || !window.confirm(t("delete_confirm", {name: editing.name}))) {
            return;
        }
        hass.callService("scene_studio", "delete_saved_scene", {id: editing.id}).then(() => {
            onSaved();
            onClose();
        }).catch(err => setError(err?.message ?? String(err)));
    };

    const next = (phase: string) => state?.next.find(n => n.phase === phase);

    return (
        <>
            <div className={"sp-overlay"} onClick={(e) => {
                if (e.target === e.currentTarget) {
                    onClose();
                }
            }}>
                <div className={"sp-sheet sp-daytime-editor"} role={"dialog"} aria-modal={"true"} aria-label={t("daytime_title")}>
                    <div className={"sp-sheet-head"}>
                        <button className={"sp-icon-btn"} aria-label={t("close")} onClick={onClose}>
                            <HaIcon icon={"mdi:close"} size={24}/>
                        </button>
                        <div className={"sp-sheet-title"}>{t("daytime_title")}</div>
                        {
                            isAdmin && state &&
                            <button className={"sp-icon-btn daytime-open-settings"} aria-label={t("daytime_settings")} title={t("daytime_settings")} onClick={() => setSettings(true)}>
                                <HaIcon icon={"mdi:clock-edit-outline"} size={24}/>
                            </button>
                        }
                    </div>
                    <div className={"sp-sheet-body"}>
                        <div className={"sp-secondary sp-small"}>{t("daytime_help")}</div>
                        <label className={"sp-field"}>
                            <span className={"sp-field-label"}>{t("name")}</span>
                            <input
                                className={"sp-input save-scene-name"}
                                type={"text"}
                                value={name}
                                placeholder={t("daytime_name_placeholder")}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </label>
                        <div className={"sp-field"}>
                            <span className={"sp-field-label"}>{t("room")}</span>
                            {
                                isAdmin ?
                                    <div className={"sp-chips wrap"}>
                                        <button className={"sp-chip" + (!areaId ? " active" : "")} onClick={() => setAreaId(undefined)}>{t("room_none")}</button>
                                        {areas.map(a => (
                                            <button key={"area_" + a.id} className={"sp-chip" + (areaId === a.id ? " active" : "")} onClick={() => setAreaId(a.id)}>
                                                {a.name}
                                            </button>
                                        ))}
                                    </div> :
                                    <div>{areaId ? areaName(hass, areaId) : t("room_none")}</div>
                            }
                        </div>

                        <div className={"sp-daytime-phases"}>
                            {PHASES.map(phase => (
                                <label key={phase} className={"sp-daytime-phase daytime-phase-" + phase + (state?.phase === phase ? " now" : "")}>
                                    <span className={"sp-daytime-phase-label"}>
                                        <HaIcon icon={PHASE_ICON[phase]} size={22}/>
                                        <span>
                                            <span className={"sp-strong"}>{t(("daytime_" + phase) as Key)}</span>
                                            <span className={"sp-secondary sp-small"}>
                                                {state?.phase === phase ? t("daytime_is_now") : (next(phase) ? t("daytime_from", {time: clock(hass, next(phase)!.at)}) : "")}
                                            </span>
                                        </span>
                                    </span>
                                    <select
                                        className={"sp-input daytime-scene"}
                                        value={scenes[phase] ?? ""}
                                        onChange={(e) => setScenes({...scenes, [phase]: e.target.value})}
                                    >
                                        <option value={""}>{t(phase === "day" ? "daytime_none" : "daytime_as_before")}</option>
                                        {
                                            inRoom.length > 0 &&
                                            <optgroup label={areaName(hass, areaId)}>
                                                {inRoom.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                                            </optgroup>
                                        }
                                        {
                                            others.length > 0 &&
                                            <optgroup label={inRoom.length > 0 ? t("daytime_other_scenes") : t("tab_scenes")}>
                                                {others.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                            </optgroup>
                                        }
                                    </select>
                                </label>
                            ))}
                        </div>

                        <SwitchRow label={t("daytime_follow")} value={follow} onChange={setFollow} className={"daytime-follow"}/>
                        <div className={"sp-secondary sp-small"}>{t(follow ? "daytime_follow_help_on" : "daytime_follow_help_off")}</div>

                        {
                            entityId &&
                            <div className={"sp-automation"}>
                                <HaIcon icon={"mdi:robot-outline"} size={20}/>
                                <div className={"sp-grow"}>
                                    <div className={"sp-secondary sp-small"}>{t("use_in_automations")}</div>
                                    <code className={"sp-entity-id"}>{entityId}</code>
                                </div>
                            </div>
                        }
                        {error && <div className={"sp-error"}>{error}</div>}
                    </div>
                    <div className={"sp-sheet-foot"}>
                        {
                            editing &&
                            <button className={"sp-btn danger save-scene-delete"} onClick={remove}>{t("delete")}</button>
                        }
                        <span className={"sp-grow"}/>
                        <button className={"sp-btn primary save-scene-confirm"} disabled={!canSave} onClick={save}>{t("save")}</button>
                    </div>
                </div>
            </div>
            {
                settings && state &&
                <DaytimeSettings hass={hass} t={t} state={state} onClose={() => setSettings(false)} onSaved={setState}/>
            }
        </>
    );
};
