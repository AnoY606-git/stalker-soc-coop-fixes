# Cordon story start fix (coop_l01_escape)

## Root causes
1. **Flash drive transferred at phrase 2, completion flag set only at phrase 4** (`configs/gameplay/dialogs_coop_l01_escape.xml:428-448`).
   Phrase 2 runs `transfer_dev_flash_sidorovich` (the flash leaves the player). `ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO` is only given by phrase 4. If the dialog is cut off between them (another player talks to Sidorovich, a player walks off or is hit, ESC, disconnect), the flash is gone and the flag was never set. The dialog's precondition (`if_actor_has_dev_flash_sidorovich`, line 419) then fails forever, so it can never be finished. Saving, reloading or re-entering the bunker doesn't help. That flag is the only thing that:
   - completes the task `esc_start_find_stalker_shustry_quest_task` (`configs/misc/tm_coop_l01_escape.ltx:34`);
   - starts the helicopter flight (`esc_helicopter_go_to_agroprom_1/2/3.ltx`, `heli_move@idle on_info`).
   So the task stays active, the helicopter never flies, and the go_to_fox chain never starts.
2. **go_to_fox depends on a flag set by a world object** (`dialogs_coop_l01_escape.xml:458`, `has_flag ESC_HELICOPTER_GO_TO_AGROPROM_INFO`).
   That flag is given only by `esc_helicopter_go_to_agroprom_1.ltx:43` (`heli_move@fly_2`, `on_game_timer`). The helicopter binder runs on the server only (`xrmpe_patch/scripts/bind_heli.script`, `if OnClient() then return`) and only while the helicopter is online. If every player is far from it (for example off on a side quest), the flight and the flag stall. The same stall happens if the heli logic is already past `fly_ready` in a bad save. The dialog has no other way in.
3. **Door** (`configs/scripts/coop_l01_escape/esc_trader_door.ltx`). The engine already evaluates `on_actor_in_zone` and `on_actor_not_in_zone` for all players, via `utils.any_player_in_zone` (`xrmpe_patch/scripts/xr_logic.script:929-936`, `utils.script:633`). So the zone check is not the problem. The problem is the toggling `on_use` in `ph_door@open` (old line 35, `on_use = ph_door@near`). Player A opens the door, and when player B presses use at the open door it switches to `near`, which closes the door in B's face. This is also how the door "closes on players".

## Changes
- `dialogs_coop_l01_escape.xml`:
  - `give_flag ESC_..._FLESH_STOP_DIALOG_INFO` is now also given in phrase 2, right when the flash is taken. The 1000 money reward moves to phrase 2 with it, so an aborted dialog doesn't lose it. Phrase 4 keeps its `give_flag`, which is harmless because `give_flag` ignores a flag that is already set. Dialog-level `dont_has_flag` is only checked at dialog start, so the dialog continues normally.
  - `go_to_fox` now requires `ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO` instead of `ESC_HELICOPTER_GO_TO_AGROPROM_INFO`. It can't be blocked by an offline helicopter.
- `esc_trader_door.ltx`: removed `on_use = ph_door@near` from `[ph_door@open]`. An open door stays open until nobody (any player) is in the space restrictor, then closes by itself.

## Not changed / limits
- Saves already stuck (flash gone, flag missing) cannot be fixed by these files, because the flesh dialog's precondition still needs the flash. A fix for those saves needs a one-off flag set via console or script. Not attempted.
- The boar side-quest report: the side-quest dialog has no shared flags with the main chain (`secondary_quests_dialog` is always available, and `dialog_13`..`dialog_21` use their own `SQ_*_STOP` flags). I found no link to go_to_fox. Phrases 5-10 of `secondary_quests_idle_dialog` have `has_flag X` and `dont_has_flag X` on the same flag, so they never show. Because of that I left them untouched. Task completion (not the dialog) rewards these quests. Not changed, so I can't say whether the boar quest itself is fixed.
- The helicopter cutscene still runs as before (if it is online). After this change Sidorovich can give the Fox quest while it is still flying. `esc_start_talk_to_the_sidorovich_quest_1_task` is only given by the heli; if it never runs, that task never appears and the Fox task from its completion is not auto-given (the Fox dialog flags are unaffected).
- I could not check the all.spawn (heli position/online range, door zone size). There is no Lua interpreter here.

## Confidence
- Flag split at phrase 2/4: high that it can lock the quest; unconfirmed that it is what the players hit.
- go_to_fox heli dependency: medium.
- Door: medium-high (the `open` toggle is clear in the config; zone and sync logic read from xrmpe_patch).

## Multiplayer risks
- Flags are server-global, so one player completing the dialog unlocks go_to_fox for everyone, as before.
- If player A is in the zone and B leaves, the door stays open for A. A door stuck open when a player stands in the zone forever is the only downside.
- The reward is now given at phrase 2 to the talking player only (same player as before).

## Test
1. New game, play to the flash. Talk to Sidorovich, pick the flash topic, and after the actor line "phrase 2" close the dialog with ESC. The task should complete, money should arrive, and the "talk about Fox" topic should appear on re-talk.
2. Repeat with the heli far away (take a side quest far from the bunker first).
3. Two players: A opens the door and walks in, B presses use on the open door. The door must stay open. After both leave the zone it closes.

## Diffs

### configs/gameplay/dialogs_coop_l01_escape.xml
```diff
--- source/gamedata.db0/configs/gameplay/dialogs_coop_l01_escape.xml	2026-10-15 20:03:12.717296500 +0100
+++ patches/cordon/gamedata/configs/gameplay/dialogs_coop_l01_escape.xml	2026-10-15 20:39:11.718325200 +0100
@@ -430,6 +430,8 @@
 
                 <text>esc_smart_terrain_1_trader_sidorovich_flesh_2</text>
 				<action>dialogs_coop_l01_escape.transfer_dev_flash_sidorovich</action>
+                <give_flag>ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO</give_flag>
+                <action>dialogs_money.give_money_to_actor_1000</action>
                 <next>3</next>
             </phrase>
             <phrase id="3">
@@ -443,7 +445,6 @@
 
                 <text>esc_smart_terrain_1_trader_sidorovich_flesh_4</text>
                 <give_flag>ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO</give_flag>
-                <action>dialogs_money.give_money_to_actor_1000</action>
                 <action>dialogs.break_dialog</action>
             </phrase>
             <phrase id="0">
@@ -455,7 +456,7 @@
         </phrase_list>
     </dialog>
     <dialog id="esc_smart_terrain_1_trader_sidorovich_go_to_fox">
-        <has_flag>ESC_HELICOPTER_GO_TO_AGROPROM_INFO</has_flag>
+        <has_flag>ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO</has_flag>
         <dont_has_flag>ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO</dont_has_flag>
         <phrase_list>
             <phrase id="1">
```

### configs/scripts/coop_l01_escape/esc_trader_door.ltx
```diff
--- source/gamedata.db0/configs/scripts/coop_l01_escape/esc_trader_door.ltx	2026-10-15 20:03:10.546738400 +0100
+++ patches/cordon/gamedata/configs/scripts/coop_l01_escape/esc_trader_door.ltx	2026-10-15 20:39:18.046991100 +0100
@@ -32,5 +32,4 @@
 snd_open_start = metal_small_open
 snd_close_start = metal_small_close_start
 snd_close_stop = metal_small_close_stop
-on_use = ph_door@near
 on_actor_not_in_zone = esc_trader_door_space_restrictor | ph_door@close
```

## Revision by lead session
- REVERTED the go_to_fox precondition change: it again requires ESC_HELICOPTER_GO_TO_AGROPROM_INFO (that flag also gates the Kuznetsov vodka chain and the "talk to Sidorovich" task, so bypassing it risked new breakage).
- ADDED a fallback in configs/scripts/coop_l01_escape/space_restrictors/esc_start_main_quest_task_space_restrictor.ltx: once the flash-drive flag is set, if the helicopter hasn't set its flag within 1800 game-seconds (~3 real min), the restrictor gives the flag and the esc_start_talk_to_the_sidorovich_quest_1_task task itself. If the helicopter fires first, the fallback just follows it.
- KEPT: flash flag + money moved to phrase 2 (fixes the cut-off dialog softlock), and the door on_use removal.

## Opening (2026-10-21)
The four co-op spawn points of this level are now inside Sidorovich's bunker (`levels\coop_l01_escape\level.game`) and his start dialog is the original SoC one
(`dialogs_coop_l01_escape.xml`, only the experienced answer). Details, tests and the Russian summary: `patches\cutscenes_pkg_opening\NOTES.md`.


## Co-op spawn points moved in front of the counter (2026-10-21)
The four team-4 / game type 128 points of `levels/coop_l01_escape/level.game` (made by `patches/cutscenes_pkg_opening/tools/gen_level_game.py`) were two inside Sidorovich's room and two in the first room BEHIND the sliding door (x -248.5 and -249.9); the engine chooses among them, so players often appeared outside the counter room. Now all four are in the room in front of his counter (x -247.8 to -246.4, z -135.1 to -133.7, y -24.8, facing him, on AI nodes). Measurements, spacing limit and the reason only three players fit at 1.4 m are in `patches/cutscenes_pkg_opening/NOTES.md`, section "Update 2026-10-21". Lobby / spectator points and game types 1 and 140 are untouched; deaths respawn at the same points.

### Кратко (RU)
Точки появления игроков (level.game) теперь все в комнате перед стойкой Сидоровича, а не за раздвижной дверью.


## Cordon after the flash drive: the original SoC chain, no helicopter flight, 500 rubles for the bridge (2026-10-21, maintainer FOSTER)

### Request
After the players hand the flash drive to Sidorovich the mod gave the task "Looks like something is up" (military helicopters fly over the village, "ask Sidorovich what is going on"), a Fox detour and other tasks of the level maker (Akasi). FOSTER wants the story to continue exactly as in original SoC: Sidorovich gives the next main tasks directly, with SoC's wording, and the bridge pass costs 500 rubles instead of 5 bottles of vodka.

### Original SoC after the flash drive (Steam SoC 1.0006: `dialogs_escape.xml`, `escape_dialog.script`, `info_l01escape.xml`, task strings)
1. Hand-in (`escape_trader_start_dialog` 521111): the flash drive is taken, `esc_serious_talk` + `tutorial_end` are set (task "Get information from the scout" ends).
2. Sidorovich's `escape_trader_jobs` ("Got any special missions for me?"): the military case talk (phrases 6, 61, 611, 6111, 61111, 611111, 6111111, 61111111, 611111111). Phrase 6111111 gives `agroprom_military_case` (+ `esc_find_railroad_passage_start`): tasks "Find the militaries' documents" (Agroprom, take them to the Barkeep, not to the trader) and "Get to the railroad embankment". The same talk offers the army outpost box job (phrase 5).
3. A task "Work for the trader" ("Get the special task from the trader") covers the time between hand-in and this talk.
4. The bridge soldiers (`esc_bridge_soldiers_start`): "the price is 500", the pass is the info `esc_bridge_pass_on`.
Fox is a separate optional contact in SoC (medkit, then the Strelok tip).

### Old (mod) vs new chain
| # | Mod (level maker) | New |
|---|---|---|
| 1 | Hand-in dialog `esc_smart_terrain_1_trader_sidorovich_flesh` (phrase 2: flash taken, flag `ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO`, 1000 money) | unchanged, and phrase 2 also gives `ESC_HELICOPTER_GO_TO_AGROPROM_INFO` silently (the helicopter used to give it) |
| 2 | 3 helicopters `esc_helicopter_go_to_agroprom_1..3` wait for the hand-in flag, fly 20 s later; helicopter 1 at the end: task "Looks like something is up", flag `ESC_HELICOPTER_GO_TO_AGROPROM_INFO`, autosave | gone: the three logic files never leave `heli_move@idle` and remove the object 3 s after it comes online (no flight, no task) |
| 3 | Task `esc_start_talk_to_the_sidorovich_quest_1_task` "Looks like something is up" | hidden (never given) |
| 4 | Sidorovich `..._go_to_fox` ("The military choppers headed somewhere...", Fox, "say hi to Kuznetsov"), needed the helicopter flag; flag `..._GO_TO_FOX_STOP_DIALOG_INFO` | same dialog id and flag, now the ORIGINAL SoC military case talk (10 phrases, SoC wording EN + RU), shown right after the hand-in. The flag is given at SoC's phrase 6111111 (a cut-off talk cannot block the chain) and at the end |
| 5 | Task "Fox might know something" (`..fox_quest_1`) | hidden |
| 6 | Task "Road to the North" (`..fox_quest_2`, target the Garbage level changer, done on arrival at the Garbage) | replaced by SoC "Get to the railroad embankment" (`esc_soc_railroad_passage_task`: same target, same completion `GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO`) and SoC "Find the militaries' documents" (`esc_soc_military_documents_task`, done when the Barkeep has the documents, `BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO`) |
| 7 | (nothing between hand-in and the helicopter) | SoC "Work for the trader" (`esc_soc_trader_job_task`), given at the hand-in, done by the military case talk |
| 8 | Kuznetsov: `go_to_fox_1` (needed the Wolf talk) "for 5 bottles of vodka", `go_to_fox_2` takes 5 vodka; task "Rest on duty" | SoC bridge dialog: "But I need to go there." / "Tough luck. Unless you REALLY need to go, then the price is 500." / "Here you are." (500 rubles taken from the talking player) / "I don't have that kind of money." (RU: "А нельзя! Но если очень хочется... то можно. Например, за пятьсот денег."). No Wolf requirement (SoC has none). Greeting as SoC: "off limits" before the pass, "keep moving" after. Task text: "Pass the army outpost: 500 rubles" (hidden like before, SoC has no such task) |
| 9 | Fox NPC dialogs (medkit, the military info after the dogs are dead), Fox's dog attack | unchanged (an optional contact like in SoC, no tasks). His help dialog still needs the Sidorovich job flag, now given by the SoC talk |
| 10 | Level maker's tasks BEFORE the hand-in (Wolf, Nimble, Petruha, ATP raid) and `esc_smart_terrain_5_helicopter` (a radio flyover after the Tolik / Petruha talk, before the hand-in) | tasks not touched; the flyover helicopter is removed too since v1.4.2 (see the section at the end) |
Not added: the army outpost box job (phrase 5 of the SoC talk): the mod's Cordon has no box object (it is not in all.spawn).

### Pass flag and the bridge logic
The pass is still the shared story flag `ESC_START_5_BOTTLES_OF_VODKA_FOR_KUZNETSOV_QUEST_TASK_INFO` (name kept): `esc_the_order_to_attack_the_players_space_restrictor` (patch any_player_restrictors) reads it, so one player paying lets the whole group through, as the vodka did. The two old Kuznetsov flags (`..GO_TO_FOX_1_STOP..`, `..GO_TO_FOX_2_STOP..`) are given with it. The money is taken by `dialogs.relocate_money_from_actor` from the player who talks (the same helper as the mod's `transfer_1000`); the precondition checks his own money.

### Files
| Patch | File |
|---|---|
| cordon | `configs\gameplay\dialogs_coop_l01_escape.xml` (flesh phrase 2, `go_to_fox` = SoC military case, Kuznetsov start / `go_to_fox_1` = SoC bridge, `go_to_fox_2` removed); the `quest_dialogs` copy was regenerated on top (`gen_quest_dialogs.py`, only its two preconditions differ) |
| cordon | `configs\misc\tm_coop_l01_escape.ltx` (the mod's file + 3 SoC tasks + new text ids for the pass task; made by `tools\make_tm_coop_l01_escape.py`) |
| cordon | `configs\scripts\coop_l01_escape\esc_helicopter_go_to_agroprom_1.ltx`, `_2`, `_3` |
| cordon | `configs\text\eng\st_cordon_soc_chain.xml`, `configs\text\rus\...` (26 strings: SoC ids copied from the Steam SoC / the Russian SoC strings; made by `tools\gen_soc_chain_text.py`) |
| cordon | `scripts\coop_soc_cordon.script` (PDA archive lines, `has_bridge_bribe`, `give_bridge_bribe`) |
| cutscenes_pkg_opening | `configs\scripts\coop_l01_escape\space_restrictors\esc_start_main_quest_task_space_restrictor.ltx` (no helicopter / vodka step any more), `scripts\coop_soc_opening.script` (the server tick gives the 3 SoC tasks to EVERY player) |
| repeatable_quests | `configs\misc\coop_hidden_tasks.ltx` (+3 ids), `configs\gameplay\character_desc_coop_l01_escape.xml` (no `go_to_fox_2` line) |
Tools: `tools\apply_soc_chain_dialogs.py` (idempotent edit of the dialog file), `tools\check_cordon_chain.py` (static proof below).

### Static chain check (offline, `python patches\cordon\tools\check_cordon_chain.py <mod source> --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`: 0 problems)
* Every Lua function and text id of the new dialogs exists (eng + rus), every flag is a known flag; every task id given in the effective Cordon logic / dialogs has a section or is hidden; every task the tick gives has a section with eng + rus title and description; the old tasks are hidden.
* The three helicopter logic files have no flight and no `give_task`; the start restrictor has no helicopter / vodka step.
* Flags the later levels read from the Cordon story, each still set: the guide votes `ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_<GAR|AGR|AGRU|VAL|X18|BAR|ROS|YAN>_INFO` (read by the Bar guide, set by the Cordon guide dialog and its restrictor, untouched), `ESC_RETURN_FROM_DV_INFO` (Dark Valley, set by the Cordon return zone of `darkvalley_restore`, independent of this chain), the level maker's own `ESC_TEST_*` flags (never set before either). Nothing in the Garbage, Agroprom, Bar or later reads `ESC_HELICOPTER_GO_TO_AGROPROM_INFO`, the Fox flags, `..GO_TO_FOX..`, the vodka pass or any of the removed tasks; the Garbage start is its own restrictor (`GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO`, on arrival).
* Flags the removed steps used to set and who sets them now: `ESC_HELICOPTER_GO_TO_AGROPROM_INFO` (hand-in dialog, silent), `..SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO` (SoC job talk), the three pass flags (the 500 rubles phrase).
Other offline checks: `tools\check_conflicts.py` (only the known overlaps, `dialogs_coop_l01_escape.xml` cordon + quest_dialogs), `tools\check_lua_escapes.py`, `tools\luabal.py` on the changed scripts, `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK (headroom 24.8 MB), `patches\cutscenes_pkg_opening\tests\camp_mock_test.py` (31 asserts: the task chain for every player and late joiners, once, at the right stage).

### Test plan (one listen-host run, automated, nothing human)
Hook `patches\cordon\tests\soc_chain_check.lua`:
```
run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socchain -ExtraDir <stage>\gamedata -Hooks patches\cordon\tests\soc_chain_check.lua -SoakSeconds 150 -ResultDir <dir>
python tools\stalker_xrmpe\qa_verdict.py <dir>
```
(stage: `python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage`). The hook fast-forwards the start chain (gives the infos of the Wolf / Nimble steps and the flash drive hand-in phrase 2) and asserts: no esc helicopter object is online; none of the old tasks (helicopter, Fox 1 and 2, vodka, kill dogs) is given; "Work for the trader" appears with its SoC title and a description; after the job talk flag the railroad and documents tasks appear with title and description; the infos for the Garbage / the guide votes are set; Sidorovich's `meet@trader` hello / bye voice is nil; the bridge helper takes exactly 500 rubles (800 to 300), the pass flag is set, `has_bridge_bribe` is false with 100 rubles. Log lines `SOCCHAIN ...`, `GIVE_TASK` lines of the tick name each player.
Not driven by the bot: the dialog windows themselves (the dialog is checked statically: functions, texts, flags). A second client in the same run (`-Clients 2` on a dedicated server) shows that the tasks reach every player (`GIVE_TASK ... player=` for each).

## Кратко (RU)
После флешки у Сидоровича теперь оригинальный сюжет ТЧ: сразу после сдачи флешки он даёт спецзадание про военные документы Агропрома (оригинальные реплики и тексты, фразы 6..611111111 диалога escape_trader_jobs) и задания "Работа на торговца", "Пробраться за железнодорожную насыпь", "Найти документы военных" (каждому игроку). Вертолёты Акаси после флешки не летают и удаляются, задание "Похоже, что-то намечается" и ветка Лиса не выдаются, нужные флаги ставятся молча в диалоге сдачи флешки. Проход через мост у майора Кузнецова стоит 500 рублей (как в ТЧ), а не 5 бутылок водки; платит любой игрок, проход действует на всю группу. Таблица "было / стало" выше.


## Sidorovich's bunker door: "I have the quest and the flash drive, but I can't get in" (v1.4 report, 2026-10-21)

Report from a player on v1.4: PDA shows "Important mission" (the flash drive task, target Sidorovich), "The beginning of beginnings" and a side task; he has the flash drive, the marker is in the rookie village at the bunker, "I can't get in". Two screenshots: the PDA map, and a view down onto a metal plate with a closed grating inside a metal floor (minimap marker exactly at the player).

### What the second screenshot is
Not a door object. `all.spawn` of Cordon has no hatch, cellar door or ladder object in the village (every physic object with door / hatch / grating / vent in its name or visual: `esc_trader_door`, the three `esc_shkaf_work_01_door`, the cabinet doors of the workshop house, `esc_ventilyator`; checked with the spawn reader on the shipped `all.spawn`). The player stands ON THE ROOF of Sidorovich's bunker: identified from the level files, not from a run: the AI map has walkable surface nodes (y -19.6) straight above the bunker rooms, the task marker (`target = esc_smart_terrain_1_trader_sidorovich`, his seat at -244.8, -24.8, -134.0) lies 5 m below the roof, and the grating is the roof of the ventilation shaft over `esc_ventilyator` (-243.9, -23.2, -133.2). It is static level geometry and not passable (the same in the original SoC). The way in is the stairs at the north-west corner of the bunker: top at about (-253.4, -20.3, -126.7), ramp down to (-254.1, -23.4, -134.4), corridor east to the sliding door `esc_trader_door` (-248.25, -24.7, -133.7), then Sidorovich's room.
The technician cellar of v1.4.1 (`patches/cordon_technician`, x -216 to -203, z -134 to -120) is 30 m away, has no hatch or door (an open gap in the south wall and a ramp with AI nodes) and is not involved.

### Cause (the part that is ours to fix): the door could not stay open
`esc_trader_door.ltx` (stock logic, kept by our v1.0 to v1.4 file) opened on use and sent the door back to `ph_door@close` in the same frame via `on_actor_not_in_zone = esc_trader_door_space_restrictor`. That zone is a box of 2.3 x 2.8 x 2.3 m at the TOP of the entrance stairs (-255.6, -19.6, -127.3), 11 m from the door. So the door stayed open only while some player stood in that small box, and a player at the door (alone, or all players together) got it open for one frame at most. In v1.4 every player also starts inside the bunker and has to get out through this door. `tools/check_door.py` runs the xr_logic switch rules over four walks and shows it: with the v1.4 file every position inside the bunker ends "closed", also right after "use".
(The flash drive hand-in itself was checked and is fine: the dialog `esc_smart_terrain_1_trader_sidorovich_flesh` is an actor dialog with `if_actor_has_dev_flash_sidorovich(first_speaker)`, which asks the TALKING player, so any carrier can hand it in; its only flag gate is `dont_has_flag ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO`, set in phrase 2 together with the flash transfer.)

### Fix (patch `cordon`, file `configs\scripts\coop_l01_escape\esc_trader_door.ltx`)
The door now follows the zone `esc_sr_no_weapon_space_restrictor` (box 17 x 6 x 12 m around the corridor from the stairs bottom, the first room and Sidorovich's room, it exists on Cordon and is the same box `stash_markers` uses as the bunker): `close` opens on use or when ANY player is inside the zone, `open` closes only when NO player is inside. `open` still has no `on_use` (the earlier fix: nobody closes it in another player's face). Result: the door is open for everyone walking down the stairs and stays open while anyone is in the bunker, also for a player standing in the doorway; it closes after the last player left; the Marked One who spawns in front of the counter has it open from the first frame. `ph_door@locked` and `ph_door@near` stay in the file (a save may store them) and lead to `close` / behave like it. Works the same for a non-story player who starts at the campfire and walks to the bunker (v1.4.1).

### Offline checks
`python patches\cordon\tools\check_door.py` (zones read from `all.spawn`, xr_logic rules, walks of 1 to 4 players, also the HEAD file for comparison: 0 failed asserts for the new file; the v1.4 file prints `OLD` for every position inside the bunker). `check_cordon_chain.py` (0 problems), `camp_mock_test.py` (ALL PASS), `check_conflicts.py` (only the expected files), build budget OK.

### In-game test (one listen-host run per mode)
Hook `tests\door_check.lua` reads the REAL door object (`db.storage[id].active_section`, `door_action:is_open()` / `is_closed()`): spawn state; flash drive given, hand-in precondition true and the hand-in flag not set; teleport out (door closes), to the stairs bottom (opens by itself), first room, "use" at the door (stays open), in front of the counter, `open_talk` with Sidorovich (is_talking), out and in again. Both modes:
```
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner doorchk -ExtraDir <stage>\gamedata -Hooks patches\cordon\tests\door_check.lua -SoakSeconds 150 -CompareTimeout 10 -ResultDir <dir>
$env:DOOR_NONSTORY = "1"      # second run: the host counts as a non-story player (campfire start)
```
Then `python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix DOOR`. Not run (offline task). Not proven in the engine: that a client's "use" press reaches the server logic (stock behaviour, untouched); the new zone logic does not depend on it.

### Кратко (RU)
Игрок на v1.4: есть задание и флешка, "зайти нельзя". На втором скриншоте он стоит на КРЫШЕ бункера Сидоровича (решётка это вентиляционная шахта над esc_ventilyator, статическая геометрия, проходить нельзя, как и в оригинале; маркер задания указывает на Сидоровича на 5 м ниже). Вход в бункер это лестница в северо-западном углу (-253.4, -20.3, -126.7) и длинный коридор до раздвижной двери. Причина на нашей стороне: дверь `esc_trader_door` закрывалась в тот же кадр, потому что зона `esc_trader_door_space_restrictor` это маленький ящик на ВЕРХУ лестницы, в 11 м от двери. Теперь дверь привязана к зоне всего бункера (`esc_sr_no_weapon_space_restrictor`): открыта, пока в бункере есть хотя бы один игрок, закрывается, когда вышел последний, открывается по "use" или сама, когда кто-то заходит. Проверка: `patches\cordon\tools\check_door.py`, игровой тест `patches\cordon\tests\door_check.lua`.

## Helicopter removal is now done by the server (2026-10-21)
`on_timer = 3000 | %=destroy_object%` in `esc_helicopter_go_to_agroprom_1/2/3.ltx` never fired in the game test (the object was still online 12 s after the
hand-in, no "releasing object" line): that logic only runs while the helicopter binder updates. `coop_soc_cordon.tick_heli` (called every second from
`coop_soc_opening.tick_server`, patch cutscenes_pkg_opening) now releases the objects named `esc_helicopter_go_to_agroprom_*` with `alife():release` as soon as
`ESC_HELICOPTER_GO_TO_AGROPROM_INFO` is set (also on a level load with the flag already set). Up to 3 scans, 4 s apart. The ltx timer stays as a second way.

## Last helicopter flyover removed (v1.4.2, 2026-10-21)
The fourth level-maker helicopter, `esc_smart_terrain_5_helicopter`, flew over the village after the Tolik / Petruha talks (before the flash drive hand-in)
and played the radio message `heli_radio_part_1` (its logic file `esc_smart_terrain_5_helicopter.ltx` of the mod: `heli_move@idle` waits for
`ESC_SMART_TERRAIN_5_WALKER_TOLIK_HELP_STOP_DIALOG_INFO` or `..PETRUHA_HELP_ATP_STOP_DIALOG_INFO`, then fly_0 to fly_4, sound, `destroy_object`). It sets no flag and
gives no task, nothing else reads it (grep over scripts, configs and dialogs). The original SoC has no such flight.
* `configs\scripts\coop_l01_escape\esc_smart_terrain_5_helicopter.ltx` (this patch): the same idle-and-remove file as the three after the hand-in, no flight, no sound.
* `scripts\coop_soc_cordon.script`: `tick_heli` (already called every second by the opening script's server tick) also releases the object named
  `esc_smart_terrain_5_helicopter` with `alife():release`, 8 s after the first tick on the level, then 2 more scans 4 s apart, with no flag needed
  (the logic timer alone does not run while the binder is not updating, see the section above). Log line `coop_soc_cordon: flyover helicopter scan N released M`.
* `tools\check_cordon_chain.py` checks the file (no `heli_move@fly`, no `play_sound`, `destroy_object`) and that the script releases the object: 0 problems.
* Not run in the game (offline task): in a Cordon run the log shows `releasing helicopter [esc_smart_terrain_5_helicopter]` about 8 s after the start and no helicopter appears after the Tolik talk.
Кратко (RU): последний вертолёт-пролёт уровнемейкера (после разговора с Толиком / Петрухой, до флешки) убран: логика сразу удаляет вертолёт, сервер тоже его освобождает (`coop_soc_cordon.tick_heli`). В SoC такого пролёта нет.
