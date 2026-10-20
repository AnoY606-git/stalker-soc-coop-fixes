# Scene package x18: the X18 dream

## What it restores
The original SoC cut-scene of the X18 lab. In the command center the poltergeist dies, the player is hit by a psi
"glitch", falls, has the rats dream (movie `x18_dream`), wakes up and a patrol order sounds over the radio. In the stock
add-on nothing plays here. This package registers the scene `x18_dream` with the Scene Director (`cutscenes_core`), so it
plays on every client with a barrier, majority skip, watchdog and "once per save".

## Original vs this package
Original (SoC all.spawn labx18 restrictor, `alife_l04u_labx18.ltx:10146-10168`, `xr_effects.script:1941-1946`, `ui_movies.xml:158-176`):

| t | original | package step |
|---|---|---|
| 0 | `dar_door3_free` given (poltergeist `on_death`), `x18_gluk` (blink.ppe, tinnitus3a, psy_blackout l/r, earthquake.anm id 1974), `radar_stop.anm` id 2506 | `pp blink`, `snd2d tinnitus3a`, `snd2d psy_blackout_l/_r`, `cam earthquake`, `cam radar_stop` |
| 9 s | `disable_ui`, `+x18_actor_fall`, `agr_u_fade.ppe` | `ui_off`, `pp agr_u_fade` |
| 12 s | `stop_cam_effector(1974)`, `start_x18_dream` (movie `dream_rats`, sound `video\dream_rats`) | `cam_stop`, tutorial `soc_dream_rats` (core block) |
| movie end | `end_x18_dream` gives `dar_x18_dream`; `prison_1.anm` | `cam prison_1` |
| +3 s | `enable_ui` | `ui_on` |
| +4.5 s | `play_snd(characters_voice\scenario\val\patrol_prikaz)` | `snd2d characters_voice\scenario\coop_l04_darkvalley\patrol_prikaz` (the add-on's copy of that file) |

Differences: pause_state is off (director rule); `+x18_actor_fall` / `+dar_x18_dream` have no mod equivalent and are not given
(nothing in the mod reads them); `agr_u_fade.ppe` is replaced by the add-on's `black_screen.ppe` when the original file is not installed.

## Trigger (server, script side)
Level `coop_l04_x18`. The mod's equivalent of `dar_door3_closed` + `dar_door3_free`:
`X18_CODEDOOR_3_LOCKED_POLTERGEIST_FLAME_INFO` (given by `x18_smart_terrain_5_m_poltergeist_space_restrictor.ltx:5` when the party enters the
poltergeist room) and `X18_CODEDOOR_3_OPEN_INFO` (given `on_death` of the poltergeist squad, `configs/misc/squad_descr_coop_l04_x18.ltx:39`).
Both set -> the director's 500 ms trigger poll (after the 6 s settle time) requests the scene. No all.spawn change, no ltx change.
Skip: majority vote (contains a movie). Late joiners and loads never replay (director baseline); `once` via `SCN_X18_DREAM_PLAYED`.

Known limit: a save made after the poltergeist died but before this package existed has both flags set and the scene never played; the dream then plays
once the first time such a save is loaded on this level (the same happens in the original for `dar_door3_free` saves).

## Files
- `gamedata/scripts/coop_scn_x18.script`: registration, trigger, steps, fallback steps.
- `gamedata/configs/ui/coop_scn_x18.xml`: `scn_x18_card` (black card with a text line; fallback when the movie is not installed). Replaces the core stub.
- `gamedata/configs/text/{eng,rus}/st_coop_scn_x18.xml`: `scn_x18_card` (rus is windows-1251).

## Original SoC files NOT in this patch (the rebuild script puts them into the owner's db)
Rebuild: `tests\rebuild_soc_media.py "<SoC install>" <out>` writes them under `<out>\gamedata\...`; pack that folder with the patch.
Scene runs without any of them (text card, no dream audio), each file only improves it.
- `textures/intro/dream_rats.ogm` (video, 27.9 MB) and `sounds/characters_voice/scenario/video/dream_rats_l.ogg`, `dream_rats_r.ogg` (the director probes the `.ogm` and both `.ogg`; any missing -> fallback card)
- `anims/camera_effects/prison_1.anm`, `anims/agr_u_fade.ppe` (missing -> no wake-up camera / `black_screen.ppe`)
- `sounds/affects/psy_blackout_l.ogg`, `psy_blackout_r.ogg`, `sounds/affects/tinnitus3a.ogg` and `anims/blink.ppe` if CoP does not have them (each step is probed and skipped silently, log lines `NOSND`)
Already in the add-on or CoP and used as is: `camera_effects/radar_stop.anm`, `camera_effects/earthquake.anm`, `anims/black_screen.ppe`, `characters_voice/scenario/coop_l04_darkvalley/patrol_prikaz.ogg`.

## Tests
`tests\hooks\x18.lua`, run: `powershell -NoProfile -ExecutionPolicy Bypass -File tests\run_scene_test.ps1 -Map coop_l04_x18 -Hook x18 -Soak 300 [-Media]`
Cases: `x18_dream_neg_partial` (LOCKED flag alone does not start it), `x18_dream` (OPEN flag -> REQUEST,GO,CLIENT_START,CLIENT_END,ACK,END all_acked, PLAYED, ui off and back on,
no engine error lines, screenshot of the dream frame), `_no_replay`, `_late_join` (baseline reset, no replay), `_input_back` (player moves), `_skip_majority` (second run, skip ends it in under 3 s, ui restored).

RESULTS_PLACEHOLDER
