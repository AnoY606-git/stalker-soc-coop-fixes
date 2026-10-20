# Scene package radar: Brain Scorcher shutdown + the radar dream

## What it restores
The original SoC scene after the Brain Scorcher is switched off: a psi blackout, the player collapses, dreams the
"sarcophagus" dream (movie `radar_dream`), then wakes to the first call of the Monolith. In the stock add-on the lab only
autosaves. This package registers the scene `radar_stop` with the Scene Director (`cutscenes_core`).

## Original vs this package
Original (`bun_deactivate_radar.ltx:5-20`, `xr_effects.script:1958-1964`, `ui_movies.xml:178-199`):

| t | original | package step |
|---|---|---|
| 0 | `+bar_deactivate_radar_done`: sound `affects\psy_blackout` (stereo pair, 16.4 s), `radar_stop.anm` id 2506 | `snd2d affects\psy_blackout_l/_r` (or `tinnitus3a` if the pair is absent), `cam radar_stop` |
| 10.5 s | `disable_ui`, `+bun_actor_fall`, `agr_u_fade.ppe` | `ui_off`, `pp agr_u_fade` |
| 16.5 s (sound end) | `start_radar_dream` (movie `dream_sarcofag`), `+sar_monolith_call`, `+bun_antenna_off` | tutorial `soc_dream_sarcofag` (core block) |
| movie end | `end_radar_dream` gives `bun_patrol_start`: `prison_1.anm` id 2506 + sound `sarcofag\monolith_call_1` | `cam prison_1`, `snd2d characters_voice\scenario\coop_l11_sarcofag\monolith_call_1` (the add-on's copy), blocking |
| call end | `enable_ui` | `ui_on` |

`radar_stop.ppe` is NOT used: in the original `postprocess.ltx` its `pp_eff_name` line is commented out, only the camera animation runs.

## Trigger and the "Brain Scorcher off" effect
Level `coop_l09_x10`. The mod switches the Brain Scorcher off (psi antenna restrictors `rad_psi_radiotion_*`, `rad_antenna_particle_*`, helicopter) when
`X10_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO` and `X10_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO` are both set. The scene is requested by the director when both flags are set
(`x10_lab_primary_switcher_2.ltx:8` gives the second one; CUTSCENES_v2 named only lever 2, but with only lever 2 the antenna is still on). The antenna-off
effect is the mod's own flag logic and is applied exactly once by those flags; the scene gives and removes no flag (the original `+bun_antenna_off`, `+sar_monolith_call`,
`+bun_patrol_start` do not exist in the mod, and the autosave in `x10_lab_primary_switcher_2.ltx` is untouched).
Skip: majority vote (movie). Late joiners and loads never replay; `once` via `SCN_RADAR_STOP_PLAYED`.

## Files
- `gamedata/scripts/coop_scn_radar.script`
- `gamedata/configs/ui/coop_scn_radar.xml`: `scn_radar_card` (fallback card). Replaces the core stub.
- `gamedata/configs/text/{eng,rus}/st_coop_scn_radar.xml`: `scn_radar_card` (rus windows-1251).

## Original SoC files NOT in this patch (rebuild script puts them into the owner's db)
`tests\rebuild_soc_media.py "<SoC install>" <out>`. The scene runs without them (text card).
- `textures/intro/dream_sarcofag.ogm` (16 MB), `sounds/characters_voice/scenario/video/dream_sarcofag_l.ogg`, `dream_sarcofag_r.ogg`
- `anims/camera_effects/prison_1.anm`, `anims/agr_u_fade.ppe`
- `sounds/affects/psy_blackout_l.ogg`, `psy_blackout_r.ogg` (16.4 s each)
Already in the add-on/CoP and used as is: `camera_effects/radar_stop.anm`, `anims/black_screen.ppe`, `characters_voice/scenario/coop_l11_sarcofag/monolith_call_1.ogg`, `affects/tinnitus3a`.

## Tests
`tests\hooks\radar.lua`: `powershell -NoProfile -ExecutionPolicy Bypass -File tests\run_scene_test.ps1 -Map coop_l09_x10 -Hook radar -Soak 300 [-Media]`
Cases: `radar_stop_neg_partial` (lever 1 alone does nothing), `radar_stop` (lever 2 flag -> full sequence, PLAYED, ui off/on, no errors, screenshot), `_no_replay`, `_late_join`, `_input_back`, `_skip_majority`.

RESULTS_PLACEHOLDER
