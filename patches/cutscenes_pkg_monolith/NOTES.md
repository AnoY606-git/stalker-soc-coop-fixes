# cutscenes_pkg_monolith: Control Monolith, C-Consciousness arrival, join / refuse choice

Restores three SoC beats in Shadow of COOP (level `coop_l11_control_monolith`), synced through the Scene Director
(`patches/cutscenes_core`, API in `CONTRACT.md`).

## Original SoC behaviour
- `sar_monolith_gen_main.ltx`: when the 6th generator dies: `run_postprocess(monolith_off:2507:false)`, sound `mon_monolith_alarm`, at its end
  `+sar_monolith_destroy`, then `play_snd(characters_voice\scenario\osoznanie\teleport_osoznanie)`.
- `mon_space_restrictor` (`alife_l12u_control_monolith.ltx`): on `sar_monolith_destroy`, 7 s later `teleport_actor(oso_actor_walk:oso_actor_look)` and
  `sr_cutscene@osoznanie_cam` (`oso_cam.anm`), at its end `oso_init_dialod` (the talk with the C-Consciousness).
- `dialogs_aes.script`: `osoznanie_agree` -> tutorial `mov_join_osoznanie` (video `dream_doctor_2`, then `xr_effects.game_credits`);
  `osoznanie_decline` -> back to the game (to stancia 2, where `mov_refuse_osoznanie` = final_peace plays).

## Scenes (all in `gamedata/scripts/coop_scn_monolith.script`)
| id | kind | trigger | what |
|---|---|---|---|
| `monolith_off` | sequence, skip any | server: flags `CON_MONOLITH_GENERATOR_1..6_INFO` all set (the mod's counters/flags of `con_monolith_generator_N.ltx`) | `monolith_off.ppe`, alarm sound, `teleport_osoznanie` voice (fallback: the add-on's `o_soznanie_call` when the voice file is missing); `on_end` requests `oso_arrival` |
| `oso_arrival` | camera, skip any | requested by `monolith_off.on_end` | `ui_off`, move to `oso_actor_walk` (17.803, -43.667, 31.283) looking at `oso_actor_look`, global camera `oso_cam`, `ui_on` |
| `oso_choice` | sequence, skip none | requested by the dialog RPC with variant `join` or `refuse` | no visuals, a news line to everybody; `on_end`: `join` -> request `end_join`, `refuse` -> server gives the dialog flag |
| `end_join` | movie, skip none | requested by `oso_choice(join)` | tutorial `scn_monolith_join` (video `intro\dream_doctor_2` + audio `characters_voice\scenario\video\dream_doctor_2`, pause off); fallback text card `scn_monolith_join_card` when the media is absent; `on_end` requests the credits |
| `mono_credits_fb` | sequence | only if the endings package has no `credits` scene | `credits_seq` tutorial, then the `main_menu` step |

Order is preserved against the original: generators -> off effect/alarm/voice -> arrival camera -> dialog. To make the mod's own
teleport to the representative (`con_zone_teleport_2_space_restrictor.ltx`) wait for the sequence, that ltx is shipped with one extra condition
(`+SCN_OSO_ARRIVAL_PLAYED` on the start state). The director always closes a scene (END at the latest after `length + grace`), so this cannot deadlock while the
director runs; a save where all six flags are already set plays `monolith_off` at the next settle (6 s) and continues.

## The join / refuse choice: who decides
The dialog phrases are client-side actions. `dialogs_coop_l11_control_monolith.xml` (shipped here, byte-identical to the mod's except the lines below) now has, in
the `..._awareness_6_dialog`, after the NPC phrase 1 two answers: phrase 2 "So be it! It is time to destroy you!" (refuse, unchanged text) and the new phrase 3
"I agree to join the C-Consciousness." (join). Both call one function (`coop_scn_monolith.oso_refuse` / `oso_join`) which ends the talk and sends an RPC
(`game_cl.executeFunctionOnServer("coop_oso_refuse"|"coop_oso_join")`). The old direct `give_flag` of `..._6_DIALOG_STOP_INFO` was removed from phrase 2.

Rule: **the player who answers decides for everyone; the first answer that reaches the server wins**, later answers are ignored (`CHOICE_IGNORED`). The server
requests `oso_choice` with that variant, the variant is stored in the shared `SCN_OSO_CHOICE_VAR_n_<VARIANT>` flag, and every client plays the same scene:
`join` -> everyone sees the same movie, then the same credits and main menu; `refuse` -> the server gives `..._6_DIALOG_STOP_INFO`, which teleports the whole
party on and starts the kill-the-representatives task for everyone (that flag is shared). Late joiners and loaded saves never replay (core baseline).

Why not a vote: xrMPE dialogs are a per-player UI and the talk with the C-Consciousness is one-to-one; a conversation choice belongs to the conversation player
(same rule as the Deus Ex HX and Skyrim Together prior art in CUTSCENES_v2). It also cannot stall: an AFK player cannot block the story, which a unanimous vote can.
The risk is that one player ends the game for everybody with `join`. Mitigation in place: the join line is a deliberate, separate answer, the movie is not skippable (ending),
and everyone gets a news line "A member of the party answered for everyone". If the owner wants a veto, a majority message box (pattern of `coop_map_vote.prompt_client`)
can be added in `accept()` for `join` only; not built.

## Files
- `gamedata/scripts/coop_scn_monolith.script` : scenes, server RPC functions (`game_sv.coop_oso_join/refuse`, injected at load and on each poll like the core does for ack/skip), dialog actions.
- `gamedata/configs/ui/coop_scn_monolith.xml` : `scn_monolith_join`, `scn_monolith_join_card`.
- `gamedata/configs/text/{eng,rus}/st_coop_scn_monolith.xml` : strings `scn_monolith_*` (Russian in windows-1251).
- `gamedata/configs/gameplay/dialogs_coop_l11_control_monolith.xml` : mod file + `<next>3</next>`, phrase 2 actions, new phrase 3.
- `gamedata/configs/scripts/coop_l11_control_monolith/space_restrictors/con_zone_teleport_2_space_restrictor.ltx` : mod file + `+SCN_OSO_ARRIVAL_PLAYED`.
- `tests/monolith.lua`, `tests/monolith_join.lua` : test hooks (copies live in the kit's `tests\hooks\`).

## Original SoC files needed (NOT in this patch; the rebuild script `tests/rebuild_soc_media.py` extracts them from the player's own SoC install)
- `anims/monolith_off.ppe` (1161 bytes)
- `anims/camera_effects/oso_cam.anm` (737 bytes)
- `sounds/characters_voice/scenario/osoznanie/teleport_osoznanie.ogg` (106,743 bytes)
- `textures/intro/dream_doctor_2.ogm` (11,077,328 bytes)
- `sounds/characters_voice/scenario/video/dream_doctor_2_l.ogg` and `dream_doctor_2_r.ogg` (about 528 KB each, 58.7 s; NOTE: CONTRACT.md says dream_doctor_2 is silent, the files exist and the original tutorial uses them)
Already in the add-on and used: `sounds/characters_voice/scenario/coop_l11_control_monolith/monolith_alarm.ogg`, `o_soznanie_call.ogg`, tutorial `credits_seq` (mod).
Every media file is probed: without them the scenes run their fallbacks (`NOPPE`/`NOCAM`/`NOSND` log lines, text card for the ending), nothing breaks.

## Needed from the endings package (see CONTRACT_REQUESTS.md)
A scene with id `credits`. `end_join.on_end` requests it when it exists, else the package's own `mono_credits_fb` (credits_seq + `main_menu`).

## Known limits
- The alarm is played 2D (the original was 3D from the generator).
- The arrival camera replaces nothing in the mod's dialog trigger: the mod's representative still starts the talk with the use key.
- The dialog action functions were tested through the real RPC, not by clicking the phrase in the UI.
