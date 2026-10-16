# Hunter's family rifle (wpn_toz34_m2) - fix notes

## Root cause
- The quest is fully wired in Bar, but nothing in scripts/configs ever creates the item:
  - Accept: `source/gamedata.db0/configs/gameplay/dialogs_coop_l05_bar.xml:1319` (`..._find_the_family_gun_quest_dialog`) gives flag `BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_STOP_DIALOG_INFO`; that triggers the task (`scripts/coop_l05_bar/space_restrictors/bar_start_find_the_family_gun_quest_task_space_restrictor.ltx:5`, `misc/tm_coop_l05_bar.ltx:42`).
  - Hand-in: dialog `..._idle_dialog` (dialogs_coop_l05_bar.xml:1355-1401) phrase 2 requires `dialogs_item.if_actor_has_family_gun` -> `first_speaker:object("wpn_toz34_m2")` (`gamedata.db1/scripts/dialogs_item.script:141-151`), transfers it, then phrase 6 gives `..._IDLE_STOP_DIALOG_INFO`, which completes the task.
  - Item section exists (`configs/weapons/w_toz34.ltx:567`, `wpn_toz34_m2`, a cut-down TOZ-34). It is referenced ONLY by those two dialog functions. No `spawn_object`, no container/stash logic, no trade/loot config creates it anywhere in the mod or xrmpe_patch scripts.
  - So the only possible source is an entry in the binary all.spawn (not in the source tree). The reports ("spawn disabled / only via console") match: it is absent or disabled there. That cannot be fixed from scripts/configs; a proper fix is adding a `wpn_toz34_m2` (or a story-id'd container) to all.spawn at the intended stash in coop_l06_rostok.
- Side note: `..._IDLE_STOP_DIALOG_INFO` is not in `story_flags_table.script`. Harmless: `story_flags.give_flag` falls back to sending the flag name as a string (id 65535).

## Change (script-based spawn, uses the mod's own pattern)
The mod already spawns quest items with `spawn_object(section:patrol_path)` from a level space_restrictor's logic (e.g. `coop_l01_escape/space_restrictors/esc_spawn_bandit_outfit_chainmail_space_restrictor.ltx`, `coop_l04_x18/.../x18_spawn_dev_document_1_3_x18_space_restrictor.ltx`; implementation `xrmpe_patch/scripts/xr_effects.script:1095`, client-safe via GM_SCRIPT_SPAWN_ENTITY).

File: `gamedata/configs/scripts/coop_l06_rostok/space_restrictors/bar_start_go_to_yantar_quest_task_space_restrictor.ltx`
- This restrictor exists in the Wild Territory level and is idle until the Yantar task. I added a first `on_info` branch: once the hunter flag is set, on the server only (`=isServer`, avoids one copy per client), spawn one `wpn_toz34_m2` and move to a copy of the original state (`start_quest_idle_gun_spawned`) that keeps the original Yantar-task logic unchanged. One-shot: after the switch it never fires again; a single shared world item, any player can pick it up and the dialog checks the talking player's inventory.
- Spawn point: existing path `ros_smart_terrain_1_yes_temp_1_walk` (a path already referenced by shipped logic in `ros_question_2_space_restrictor.ltx`, so it exists and `abort()` for a missing path cannot trigger). I could not read level data, so this location is a guess: change the path name after `wpn_toz34_m2:` to wherever the rifle should lie. A proper spot needs a new way_object in the level (editor, binary) - then use that name.

## Diff
```diff
--- ../../source/gamedata.db0/configs/scripts/coop_l06_rostok/space_restrictors/bar_start_go_to_yantar_quest_task_space_restrictor.ltx	2026-10-15 20:03:10.865638500 +0100
+++ gamedata/configs/scripts/coop_l06_rostok/space_restrictors/bar_start_go_to_yantar_quest_task_space_restrictor.ltx	2026-10-15 20:39:14.737195200 +0100
@@ -2,7 +2,12 @@
 active 												= sr_idle@start_quest_idle
 
 [sr_idle@start_quest_idle]
-on_info 											= {+BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} sr_idle@nil %+BAR_START_GO_TO_YANTAR_QUEST_TASK_INFO =give_task(ros_start_go_to_yantar_quest_task)%
+;Hunter's family rifle: spawn once (server only) when the quest has been accepted in the Bar
+on_info											= {=isServer +BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_STOP_DIALOG_INFO} sr_idle@start_quest_idle_gun_spawned %=spawn_object(wpn_toz34_m2:ros_smart_terrain_1_yes_temp_1_walk)%
+on_info2											= {+BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} sr_idle@nil %+BAR_START_GO_TO_YANTAR_QUEST_TASK_INFO =give_task(ros_start_go_to_yantar_quest_task)%
 ;on_info 											= {-BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} sr_idle@nil %+BAR_START_GO_TO_YANTAR_QUEST_TASK_INFO =give_task(ros_start_go_to_yantar_quest_task)%
 
+[sr_idle@start_quest_idle_gun_spawned]
+on_info 											= {+BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} sr_idle@nil %+BAR_START_GO_TO_YANTAR_QUEST_TASK_INFO =give_task(ros_start_go_to_yantar_quest_task)%
+
 [sr_idle@nil]
\ No newline at end of file
```

## Confidence / risks
- Root cause (no spawn in scripts): high. That the item is missing in all.spawn: medium-high (cannot inspect binary).
- Patch works mechanically (copies established pattern): medium; untested in game, no Lua/engine here. The spawn location is a placeholder.
- Limitation: if the Yantar task flag (`..._HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO`) is already set when the level loads, the restrictor is already `nil` and the rifle is not spawned; the hunter quest must be accepted before the Yantar task is handed out (normal order in Bar). Saves made after that stage are unaffected by the patch.
- If all.spawn does contain the rifle somewhere, players get a second copy (harmless).
- Multiplayer: server-only guard prevents duplicates from clients; hand-in transfers from the talking player only. A reload from an older save re-runs the one-shot.

## Test
1. Copy `gamedata\` over the game's gamedata. New game or save before accepting the hunter quest in Bar.
2. Talk to the hunter (Bar), accept ("find the family rifle"); confirm task appears.
3. Travel to the Wild Territory (coop_l06_rostok) with 2 players; walk to the spawn path and confirm exactly one TOZ-34 lies there (no abort in log).
4. Either player picks it up, returns to the hunter, "Found it, here's your rifle": rifle removed from that player, reward line plays, task completes.

## Revision by lead session
Rewrote the restrictor so the rifle spawns regardless of order: whether the hunter quest is accepted before or after the Barman docs hand-in (Yantar task), the server spawns one wpn_toz34_m2 at ros_smart_terrain_1_yes_temp_1_walk (the arrival point used by the Bar -> Wild Territory transition teleport) when the hunter flag is set and someone is on this level. Clients drop to sr_idle@nil once the Yantar task is given.
