# Cutscene core: the Scene Director

## What it is
Infrastructure for synced cut-scenes in Shadow of COOP 8.x. The original SoC movies, dreams and endings are restored by separate
packages (`patches/cutscenes_pkg_<name>`) that register scenes against this director. Nothing here changes gameplay by itself.
API for packages: `%USERPROFILE%\Downloads\SoC_COOP_cutscenes\CONTRACT.md`. Design: `CUTSCENES_v2.md`.

## Why (root cause in the stock add-on)
- `run_tutorial` starts a movie locally on whoever's logic copy runs it: no barrier, no end signal, no shared decision.
- `sr_cutscene` lets any single player's skip stop the scene on every machine, and nobody waits for anybody.
- Endings were a per-client dice roll and never reached the credits; the opening movie was never started (xrMPE skips the engine intro).

## How it works
- Server tick (500 ms): evaluates scene triggers, picks a variant once, publishes `SCN_<ID>_VAR_<n>_<v>` and `SCN_<ID>_GO_<n>`
  with `story_flags.give_flag` (shared, saved with the game, sent to late joiners).
- Every client tick (50 ms) sees GO after its own baseline and plays the step list locally (movie tutorial, camera .anm, postprocess,
  sounds, UI off/on, teleport), then sends `game_cl.executeFunctionOnServer("coop_scn_ack")`.
- The server gives `SCN_<ID>_END_<n>` + `SCN_<ID>_PLAYED` when every player alive at GO acked, or at `length + grace` (timeout), or on a skip.
  Skip policy per scene: `majority` (movies), `any` (camera), `none` (endings), Jump key, vote RPC `coop_scn_skip`.
- Client watchdog: releases tutorial/camera/pp/UI at `length + grace + 5 s` even if END never arrives.
- Baseline: the first client tick after the local actor exists records the existing GO flags; loads and late joiners never replay.
  A GO without END after a load is closed by the server as `orphan`.
- Asset probe: `need = {tex=, snd=}` is checked with `getFS():exist` before the scene runs; missing files run the scene's `fallback`.
- `coop_scenes.on_first_spawn(fn)`: server hook once per player name when the story character (`actor_the_main_character`) is alive
  outside the lobby (105,-15.8,-9.8, r=25); flag `SCN_FS_<NAME>` stops repeats. This is the entry point for "start in Sidorovich's bunker".
- Party stats helper `coop_scenes.party()` returns summed money and reputation of all alive players (owner decision for the endings).

## Files
- `gamedata/scripts/coop_scenes.script`: the director. Injects at runtime (no dscript needed): `game_sv.coop_scn_ack/skip`, `xr_effects.scene_request`.
- `gamedata/scripts/xr_conditions.dscript`: the mod's file unchanged + a 10 line bootstrap (`scene_played`, `scene_active` conditions,
  `coop_scenes.install()`). It is the only way the director is loaded. Anyone else who needs `xr_conditions.dscript` must append to THIS file.
- `gamedata/configs/ui/game_tutorials.xml`: the mod's file + `#include` of `ui_soc_scenes.xml` and one `coop_scn_<name>.xml` per package.
- `gamedata/configs/ui/ui_soc_scenes.xml`: `scene_test_3s`, `soc_black`, movie wrappers (`soc_intro`, `soc_dream_*`, `soc_end_*`).
- `gamedata/configs/ui/coop_scn_<name>.xml`: empty stubs (11 package names); a package ships its own file at the same path
  (patch dir `cutscenes_pkg_<name>` sorts after `cutscenes_core`, so build.py lets it win).
- `gamedata/configs/text/{eng,rus}/st_coop_scenes.xml`: `scn_core_skip_hint`.

## xr_effects.dscript
Deliberately NOT shipped by this patch. `patches/cnpp_shake/gamedata/scripts/xr_effects.dscript` (SoC original +
`surge_shock_pp_eff = 20080402`) and `optional/sarcophagus_fps/.../xr_effects.dscript` (same + squad trim) are untouched and stay consistent.

## Risks / not verified
See "Test results" below once run. Unverified without a real second client: remote-client flag delivery order (VAR before GO relies on
reliable ordered events), `is_action_pressed(kJUMP)` during a playing tutorial, disconnect after credits.
The tick is re-armed by `ensure()` when it has not run for 4 s (level reload).

## Test
Kit: `%USERPROFILE%\Downloads\SoC_COOP_cutscenes\tests\run_scene_test.ps1` (see CONTRACT.md section 9).
`run_scene_test.ps1 -Map coop_l01_escape -Hook core` runs T0 to T10 on a listen server with a hands-free bot.

## Test results (listen server, coop_l01_escape, real game, 2026-10-18)
`run_scene_test.ps1 -Hook core`: 16 cases, all PASS: install + flag + RPC round trip, first-spawn hook, movie cycle (3.5 s, ordered
REQUEST/GO/CLIENT_START/CLIENT_END/ACK/END, PLAYED set, second request ignored), camera cycle, skip any / majority 1 of 1 (ends in under
150 ms) / none (ignored), ack-blocked timeout (4.0 s), watchdog (7.0 s), asset-probe fallback, queue order, targeted run, variant flow,
baseline reset (no replay), input back (player moves).
Not tested: save/load and level reload (T3), a second real client (T13), disconnect after credits (`main_menu` step), real media (T11).
