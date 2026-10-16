# Bar Arena (Arnie) fix - notes

## Is the arena implemented?
Yes. Dialogs (dialogs_coop_l05_bar.xml `bar_smart_terrain_2_stalker_arny_arena_dialog` / `..._victory_arena_dialog`, attached to Arnie in character_desc_coop_l05_bar.xml:202-203), squads (squad_descr_coop_l05_bar.ltx), spawn/start/stop/cat-scene restrictors (scripts/coop_l05_bar/space_restrictors/arena_arny/) and `story_flags_table.script` flags all exist. Betting on stalkers-vs-mutants is deliberately disabled by the authors (`<next>4</next>` commented out in the dialog, the stalkers stop restrictor's `determine_cl_sv` transitions commented out). I left that alone.

## Bug 1 - Arnie only brushes players off
Root cause: squad_descr_coop_l05_bar.ltx:245-250 puts Arnie in a squad with a second NPC (`npc = bar_smart_terrain_2_stalker_arny, sim_default_stalker_4`). His logic file (configs/scripts/coop_l05_bar/bar_smart_terrain_6_guard_arny.ltx) says `meet = meet` but defines no `[meet]` section, so xr_meet uses its defaults (source_base/xrmpe_patch/scripts/xr_meet.script:557-558): `use = {...} {!is_squad_commander} false, ...` and `snd_on_use = ... {!is_squad_commander} meet_use_no_talk_leader`. If Arnie is not the squad commander, `use` is false and pressing use plays the "go talk to the squad leader" line (the "go roll on Bugor's ears" brush-off). His dialogs (start + arena + victory) never open. (The mod author hit the same default: their unloaded copy `gamedata.db1/scripts/Новая папка/xr_meet.script:558` removes the `is_squad_commander` check, but it sits in a subfolder and is not loaded.)
Fix: add an explicit `[meet]` section to bar_smart_terrain_6_guard_arny.ltx, modeled on Plyushkin's (`bar_smart_terrain_10_animpoint_plyushkin.ltx:20-33`): `use = {=actor_enemy} false, true`. Scoped to Arnie only; no global script change.

## Bug 2 - teleported to Arnie on every Bar entry
Mechanism (static analysis): the arena is driven by story flags (server-global, saved). Start/stop restrictors are `type = no_save`, so their logic restarts at every level load in `determine_cl_sv -> sv_control`; if any control flag is still set, they act on it: the stop restrictors (`..._stop_arena_battle_players_vs_mutants*_space_restrictor.ltx`) wait 20 s and call `xrmpe_teleport_actors(bar_smart_terrain_6_arena_spawn_players_2_*)`, the start ones teleport to `..._players_1_*`; the cat-scene restrictor teleports local actors via `sr_cutscene` `point =` (sr_cutscene.script `zone_enter`) whenever `START_CAT_SCENE_INFO` is set. The flags are cleared by several restrictors all racing on the same `*_SQUAD_DEAD` flag (stop restrictor, spawn restrictor, cat-scene restrictor each `%-FLAG%` it; whichever runs first starves the others, e.g. cat scene never clears `START_CAT_SCENE_INFO`/`START_ARENA_GO`, spawn restrictor stays in `start_arena_spawn_*`). Stale flags then survive saves/level changes and re-fire on every Bar load. The cat-scene restrictor was also saved (no `type = no_save`), so it could stay stuck in `..._dead_mutant_idle`.
I could not run the game, so I cannot say which single stale flag you had; the fix resets all of them.
Fix (all at level load, server side only, in the transition out of `determine_cl_sv`):
- both stop restrictors: `%-...SQUAD_DEAD%` for every DEAD / DTT_DEAD flag they consume;
- three start restrictors: clear every `*_ARENA_INFO`, `*_DURING_THE_TIME_ARENA_INFO`, `BET_START_ARENA_INFO` (+ `START_CAT_SCENE_INFO`, `START_ARENA_GO` in the players_vs_mutants one);
- cat-scene restrictor: now `type = no_save`, new first state `sr_idle@idle_reset` that clears `START_CAT_SCENE_INFO`/`START_ARENA_GO` on the server and enters `idle_start_cat_scene`.
`*_DEAD_FAIL` flags (used by the reward dialog) and `SPAWN_*` flags are not touched, so unclaimed rewards are kept.

## Files changed (install as loose files in gamedata\)
All under `configs/scripts/coop_l05_bar/` (CRLF/cp1251 preserved, byte-copy + minimal edit):
- bar_smart_terrain_6_guard_arny.ltx
- space_restrictors/arena_arny/bar_actor_cat_scene_space_restrictor.ltx
- space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_players_vs_mutants_space_restrictor.ltx
- space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_players_vs_mutants_during_the_time_space_restrictor.ltx
- space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_stalkers_vs_mutants_space_restrictor.ltx
- space_restrictors/arena_arny/bar_smart_terrain_6_stop_arena_battle_players_vs_mutants_space_restrictor.ltx
- space_restrictors/arena_arny/bar_smart_terrain_6_stop_arena_battle_players_vs_mutants_during_the_time_space_restrictor.ltx

## Confidence
- Bug 1: medium-high. The default-`use` / `is_squad_commander` / `meet_use_no_talk_leader` chain matches the symptom exactly; not confirmed that Arnie really is a non-commander at runtime (squad commander is chosen by the sim).
- Bug 2: medium-low. The mechanism (stale flags re-fired at level load) is real in the configs, but the exact stale flag was not identified without running the game. Existing saves with the stale state are healed on the next Bar load.

## Multiplayer risks
- Flags are cleared on the server branch only; clients receive changes via the normal flag sync. On a listen server `isServer`/`isClient` can both be true; the first transition (`isServer`) wins, as in the original.
- A level load while a fight is genuinely running (not possible via normal play) would cancel it.
- Making the cat-scene restrictor `no_save` means a save made mid-cutscene resumes at idle instead of the cutscene.
- Stalkers-vs-mutants betting remains disabled by the authors; I did not enable it.

## How to test
1. Bar, talk to Arnie with weapons holstered/drawn: arena menu ("Which one?") must open; no brush-off line.
2. Pick "Fight against dogs", get teleported to the arena after ~20 s, win; after ~20 s you are returned; collect the reward via "I want to collect my reward".
3. Leave to another level, return to the Bar (repeat 2-3 times, and also load an old save made after an arena fight): you must spawn at the normal transition point with no teleport and with UI enabled.
4. Repeat with a timed fight and let the timer run out.

## Diffs (tabs collapsed for readability; line endings CRLF in the real files)
```diff
--- a/./bar_smart_terrain_6_guard_arny.ltx
+++ b/./bar_smart_terrain_6_guard_arny.ltx
@@ -16,4 +16,19 @@
 trade_enable  = false
 ;meet_dialog  = {+BAR_ARNY_ARENA_SMART_TERRAIN_DOG_SQUAD_DEAD_FAIL} bar_smart_terrain_2_stalker_arny_arena_pvm_1_start, {+BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_SQUAD_DEAD_FAIL} bar_smart_terrain_2_stalker_arny_arena_pvm_2_start,  {+BAR_ARNY_ARENA_SMART_TERRAIN_BOAR_SQUAD_DEAD_FAIL} bar_smart_terrain_2_stalker_arny_arena_pvm_3_start, {+BAR_ARNY_ARENA_SMART_TERRAIN_BLOODSUCKER_SQUAD_DEAD_FAIL} bar_smart_terrain_2_stalker_arny_arena_pvm_4_start
 
+[meet]
+close_snd_hello  = nil
+close_snd_bye  = nil
+close_anim  = nil
+close_victim  = nil
+far_anim  = nil
+far_victim  = nil
+close_distance  = 0
+far_distance  = 0
+close_snd_distance  = 3
+abuse  = false
+use  = {=actor_enemy} false, true
+allow_break  = true
+meet_on_talking  = true
+
 ;================================================
\ No newline at end of file
--- a/./space_restrictors/arena_arny/bar_actor_cat_scene_space_restrictor.ltx
+++ b/./space_restrictors/arena_arny/bar_actor_cat_scene_space_restrictor.ltx
@@ -1,5 +1,10 @@
 [logic]
-active  = sr_idle@idle_start_cat_scene
+active  = sr_idle@idle_reset
+type  = no_save
+
+[sr_idle@idle_reset]
+on_info  = {=isServer} sr_idle@idle_start_cat_scene %-BAR_ARNY_ARENA_SMART_TERRAIN_START_CAT_SCENE_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_START_ARENA_GO%
+on_info2  = {=isClient} sr_idle@idle_start_cat_scene
 
 [sr_idle@idle_start_cat_scene]
 on_player_inside  = sr_idle@idle_start_cat_scene_idle %=disable_ui =run_postprocess(blink)%
--- a/./space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_players_vs_mutants_during_the_time_space_restrictor.ltx
+++ b/./space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_players_vs_mutants_during_the_time_space_restrictor.ltx
@@ -3,7 +3,7 @@
 type  = no_save
 
 [sr_idle@determine_cl_sv]
-on_info  = {=isServer} sr_idle@sv_control
+on_info  = {=isServer} sr_idle@sv_control %-BAR_ARNY_ARENA_SMART_TERRAIN_DOG_DURING_THE_TIME_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_DURING_THE_TIME_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_BOAR_DURING_THE_TIME_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_BLOODSUCKER_DURING_THE_TIME_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_NON_DURING_THE_TIME_ARENA_ARENA_INFO%
 on_info2  = {=isClient} sr_idle@cl_control
 
 ;server logic
--- a/./space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_players_vs_mutants_space_restrictor.ltx
+++ b/./space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_players_vs_mutants_space_restrictor.ltx
@@ -3,7 +3,7 @@
 type  = no_save
 
 [sr_idle@determine_cl_sv]
-on_info  = {=isServer} sr_idle@sv_control
+on_info  = {=isServer} sr_idle@sv_control %-BAR_ARNY_ARENA_SMART_TERRAIN_DOG_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_BOAR_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_BLOODSUCKER_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_NON_ARENA_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_START_CAT_SCENE_INFO -BAR_ARNY_ARENA_SMART_TERRAIN_START_ARENA_GO%
 on_info2  = {=isClient} sr_idle@cl_control
 
 ;server logic
--- a/./space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_stalkers_vs_mutants_space_restrictor.ltx
+++ b/./space_restrictors/arena_arny/bar_smart_terrain_6_start_arena_battle_stalkers_vs_mutants_space_restrictor.ltx
@@ -3,7 +3,7 @@
 type  = no_save
 
 [sr_idle@determine_cl_sv]
-on_info  = {=isServer} sr_idle@sv_control
+on_info  = {=isServer} sr_idle@sv_control %-BAR_ARNY_ARENA_SMART_TERRAIN_BET_START_ARENA_INFO%
 on_info2  = {=isClient} sr_idle@cl_control
 
 ;server logic
--- a/./space_restrictors/arena_arny/bar_smart_terrain_6_stop_arena_battle_players_vs_mutants_during_the_time_space_restrictor.ltx
+++ b/./space_restrictors/arena_arny/bar_smart_terrain_6_stop_arena_battle_players_vs_mutants_during_the_time_space_restrictor.ltx
@@ -3,7 +3,7 @@
 type  = no_save
 
 [sr_idle@determine_cl_sv]
-on_info   = {=isServer} sr_idle@sv_control
+on_info   = {=isServer} sr_idle@sv_control %-BAR_ARNY_ARENA_SMART_TERRAIN_DTT_DOG_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_DTT_PSEUDODOG_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_DTT_BOAR_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_DTT_BLOODSUCKER_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_DTT_NON_SQUAD_DEAD%
 on_info2   = {=isClient} sr_idle@cl_control
 
 ;server logic
--- a/./space_restrictors/arena_arny/bar_smart_terrain_6_stop_arena_battle_players_vs_mutants_space_restrictor.ltx
+++ b/./space_restrictors/arena_arny/bar_smart_terrain_6_stop_arena_battle_players_vs_mutants_space_restrictor.ltx
@@ -3,7 +3,7 @@
 type  = no_save
 
 [sr_idle@determine_cl_sv]
-on_info   = {=isServer} sr_idle@sv_control
+on_info   = {=isServer} sr_idle@sv_control %-BAR_ARNY_ARENA_SMART_TERRAIN_DOG_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_BOAR_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_BLOODSUCKER_SQUAD_DEAD -BAR_ARNY_ARENA_SMART_TERRAIN_NON_SQUAD_DEAD%
 on_info2   = {=isClient} sr_idle@cl_control
 
 ;server logic
```
