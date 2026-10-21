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
