# Scene package yantar: X16 brain shutdown + doctor dream, and the ghost sleep

## What it restores
Two original SoC scenes of the Yantar chapter, registered with the Scene Director (`cutscenes_core`):
- `yantar_brain` (level `coop_l08_x16`): the X16 brain is switched off, psi blackout, the player collapses and dreams the doctor dream (movie `yantar_dream`, 78 s), wakes up.
- `yantar_ghost_sleep` (level `coop_l08_yantar`): the psi "ghost" sleep of the research scene: fade, wake-up filter, looped `dream.anm`, `prison_0/1.anm` (no movie).

## yantar_brain: original vs package
Original (`yan/brain_system_message.ltx:26-40`, `xr_effects.script:1923-1927`, `ui_movies.xml:201-219`):

| t | original | package step |
|---|---|---|
| 0 | `yan_labx16_switcher_primary_off`: `yan_gluk` (psy_blackout l/r + earthquake.anm id 1974) and sound `system_message_3` | `snd2d psy_blackout_l/_r` (or tinnitus3a), `cam earthquake` |
| 1 s | `radar_stop.anm` id 2506 | `cam radar_stop` |
| 10 s | `agr_u_fade.ppe` | `pp agr_u_fade` |
| 13 s | `start_yantar_dream` + `disable_ui` (movie: video `dream_doctor`, sound `video\dream_doctor`) | `cam_stop`, `ui_off`, tutorial `scn_yantar_dream` (own block with the sound pair) |
| movie end | `end_yantar_dream` gives `yantar_find_ghost_task_start`: `prison_1.anm` id 2508 | `cam prison_1` |
| +4 s | `enable_ui` | `ui_on` |

Not reproduced: `system_message_3` (the mod's lever 4 already plays `system_message_1` on the press; a second voice would overlap) and the info
`yantar_find_ghost_task_start` (the mod has no ghost task). Trigger (server): all four `X16_LAB_PRIMARY_SWITCHER_n_DEACTIVATE_INFO` flags (the mod's psi field
`x16_psi_radiotion_75` ends on the same four). `patches/x16` sets lever n's flag on the press, so the scene starts at the 4th press; that patch's logic and autosave are untouched.
(`patches\x16_levers` named in the brief does not exist in the tree; the lever fix is `patches\x16`.)
Skip: majority vote. `once` via `SCN_YANTAR_BRAIN_PLAYED`.

## yantar_ghost_sleep: original vs package
Original (`yan/yan_sleep_restrictor.ltx:1-20`): `+yan_spawn_ghost` (given in `gulag_yantar.ltx` by the wounded scientist stage `remark@scientist_wounded_1`):
`yan_gluk` -> 3 s `agr_u_fade` -> 2.5 s `deadcity_wake.ppe`, teleport to the hidden bed, `dream.anm` looped (id 1002), `yan_dream_voices`, `disable_ui` -> 15 s -> back, 3 s,
`prison_0.anm` looped (1003) -> 7 s -> `prison_1.anm`, `enable_ui`. Package: same timeline (5.5 s gluk and fade with control, then 15 s dream, 3 s, 7 s), ending at 30.5 s.
- The mod has no `yan_spawn_ghost` and no gulag scene, so the trigger is a position: any alive player within 10 m of (174.65, -7.80, -99.65), the research stop of the
  SoC scientists (`way_l08_yantar.ltx` `yan_scientist_wait_walk_3`; the mod level uses SoC coordinates), while `SCN_YANTAR_BRAIN_PLAYED` is not set (the SoC ghost sleep precedes the X16 dream). This is an approximation of a gulag-driven event; if the party never walks past that stop the scene does not play.
- The hidden-bed teleports (`yan_actor_sleep_1`, `yan_actor_sleep`) are left out: in co-op everyone sleeps where they stand.
- `dream_talk_l/_r` voices are played if the files exist (they are not in the media set, so currently silent).
- Looped cameras: the director's `cam` step cannot loop (request in `CONTRACT_REQUESTS.md`); `fn` steps start/stop `level.add_cam_effector(..., true)` themselves and
  `on_client_end` removes them on every end path (done, skip, stopped, watchdog).
Skip: anyone (camera scene). `once` via `SCN_YANTAR_GHOST_SLEEP_PLAYED`. Late joiners and loads never replay.

## Files
- `gamedata/scripts/coop_scn_yantar.script`: both scenes.
- `gamedata/configs/ui/coop_scn_yantar.xml`: `scn_yantar_dream` (movie + `dream_doctor` sound pair), `scn_yantar_card` (fallback card). Replaces the core stub.
- `gamedata/configs/text/{eng,rus}/st_coop_scn_yantar.xml`: `scn_yantar_card` (rus windows-1251).

## Original SoC files NOT in this patch (rebuild script puts them into the owner's db)
`tests\rebuild_soc_media.py "<SoC install>" <out>`. Both scenes run without them (movie scene shows a text card).
- `textures/intro/dream_doctor.ogm` (15.8 MB), `sounds/characters_voice/scenario/video/dream_doctor_l.ogg`, `dream_doctor_r.ogg` (78.4 s; the original DOES have sound, unlike what CONTRACT says)
- `anims/camera_effects/prison_0.anm`, `prison_1.anm`, `anims/agr_u_fade.ppe`, `anims/deadcity_wake.ppe`
- `sounds/affects/psy_blackout_l.ogg`, `psy_blackout_r.ogg`
Already in the add-on/CoP: `camera_effects/radar_stop.anm`, `earthquake.anm`, `dream.anm` (CoP), `anims/black_screen.ppe`, `affects/tinnitus3a`.

## Tests
`tests\hooks\yantar_brain.lua` (`-Map coop_l08_x16`) and `tests\hooks\yantar_sleep.lua` (`-Map coop_l08_yantar`):
`powershell -NoProfile -ExecutionPolicy Bypass -File tests\run_scene_test.ps1 -Map <level> -Hook <hook> -Soak 300 [-Media]`
Cases per scene: negative trigger (3 of 4 levers / far from the research stop), the scene by its real trigger (full sequence, PLAYED, ui off/on, no errors, screenshot),
`_no_replay`, `_late_join`, `_input_back`, `_skip_majority` (brain) / `_skip_any` (sleep).

RESULTS_PLACEHOLDER
