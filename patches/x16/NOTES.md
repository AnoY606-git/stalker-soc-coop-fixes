# X16 lab: Controller door / levers fix

## Symptoms
Door to the Controller (`x16_door_trader`) stays shut after dying in the lab or loading a save made after the 4th lever. Levers sometimes ignore F.

## Root cause (analysis; no engine/runtime access, so partly inferred)
- Door logic is fine: `source/gamedata.db0/configs/scripts/coop_l08_x16/x16_door_trader.ltx:3-21` opens when the four story flags
  `X16_LAB_PRIMARY_SWITCHER_{1..4}_DEACTIVATE_INFO` are set (upper-case names = global story flags, `xr_logic.script:1037,704`, saved by `game_sv.script:5`).
  The whole door state therefore depends on whether those flags are present after a load.
- The flags were set only as a side effect of a timed intermediate section (`ph_idle@system_message_N`, 500 ms after the press), not on the press itself
  (`x16_lab_primary_switcher_1..4.ltx` original lines 12-14), and the lever ended in a dead-end `[ph_idle@nil]` that never re-checks the flag.
  Any save/death/reload landing between the press and the flag, or a lost flag, leaves lever = "done" (unusable, no response to F) and door flag missing: nothing can ever repair it.
  Compare the working X10 lab (`coop_l09_x10/x10_lab_primary_switcher_1.ltx`), which sets the flag in `on_press` and has `on_info` both ways.
- Lever 4 additionally runs `=scenario_autosave(...)` inside a section-level `on_info` with no guard (original line 14). Per `xr_logic.script:910-911` an on_info
  with no target section re-fires its effects on every update while the section is active (up to 5 s), including right after loading that very autosave
  (section saved as `system_message_1`). So loading "st_get_out_of_the_lab" re-triggers console `save` repeatedly while the level is still initialising,
  and it overwrites the save with half-initialised state. This matches "the switch is the trigger / loading a save after the last switch breaks it".
- Confidence: medium. Flag-vs-section desync and the autosave re-fire are verified in the scripts; I could not verify the engine-side save timing.

## Changes (only `x16_lab_primary_switcher_1..4.ltx`, copied from mod gamedata.db0)
1. `active`: `on_info = {+FLAG_n} ..._done` (lever shows as used if its flag is set); `on_press` now also does `+FLAG_n` immediately.
2. New terminal section `ph_button@x16_lab_button_n_done` (anim off, no on_press) with `on_info = {-FLAG_n} ..._active` (self-heals if flag is missing, lever usable again).
   Replaces the dead-end `ph_idle@nil` as the target of the 5 s timer. `[ph_idle@nil]` is kept (with the same two-way on_info) so old saves whose active_section is `ph_idle@nil` still load (a missing section would abort).
3. Lever 4: autosave and the flag are guarded: `on_info = {-X16_LAB_AUTOSAVE_DONE} %+FLAG_4 +X16_LAB_AUTOSAVE_DONE =play_sound =scenario_autosave%`,
   so it runs once and never again on load. `X16_LAB_AUTOSAVE_DONE` is a new upper-case story flag (not in story_flags_table; the code path handles unknown names via id 65535 + name, `story_flags.script:give_flag`).
Door file is unchanged. Door/psi zone conditions already key off the same flags, so they now recover.

## Multiplayer risks
- Flag is set on press (server side logic) instead of 500 ms later: psi zone (`x16_psi_radiotion_75`) may lift ~0.5 s sooner after the 4th lever; negligible.
- Flags are global, so one player's press counts for all; unchanged.
- New flag name relies on the 65535+string fallback in save/load/net sync; if a build lacks that path the autosave simply would not be guarded (worst case = old behaviour).
- Lever 4 intermediate section only plays sound once now (previously spammed each frame).
- Not addressed: psi helmet missing after load. It is given via Sakharov dialog (`dialogs_coop_l08_yantar.xml:83-104`, `give_flag ..._STOP_DIALOG_INFO`) per player; that is a separate dialog/inventory issue.

## Test
1. New game to the lab, press levers 1-3, save, load: levers show used, don't respond. Press 4: autosave happens once; door opens.
2. Load "st_get_out_of_the_lab" repeatedly (host and joining client): door open every time, no repeated save spam in console.
3. Die in the lab after lever 4 and respawn/reload: door open.
4. Load an old save made with the original files and a lever already used: loads without abort, lever state follows its flag.

## Diffs
```diff
--- source/gamedata.db0/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_1.ltx	2026-10-15 20:03:10.990221600 +0100
+++ patches/x16/gamedata/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_1.ltx	2026-10-15 20:40:04.442320300 +0100
@@ -4,7 +4,8 @@
 [ph_button@x16_lab_button_1_active]
 anim = lab_primary_switcher_idle
 tooltip = st_primary_switcher_idle_off_desc
-on_press = ph_button@x16_lab_button_1_deactivate %=run_cam_effector(surge_01)%
+on_info = {+X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO} ph_button@x16_lab_button_1_done
+on_press = ph_button@x16_lab_button_1_deactivate %=run_cam_effector(surge_01) +X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO%
 
 [ph_button@x16_lab_button_1_deactivate]
 anim = lab_primary_switcher_off
@@ -12,6 +13,12 @@
 
 [ph_idle@system_message_2]
 on_info = %+X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO =play_sound(system_message_2)%
-on_timer = 5000 | ph_idle@nil
+on_timer = 5000 | ph_button@x16_lab_button_1_done
 
-[ph_idle@nil]
\ No newline at end of file
+[ph_button@x16_lab_button_1_done]
+anim = lab_primary_switcher_off
+on_info = {-X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO} ph_button@x16_lab_button_1_active
+
+; kept so saves made with the old logic (active_section = ph_idle@nil) still load
+[ph_idle@nil]
+on_info = {+X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO} ph_button@x16_lab_button_1_done, {-X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO} ph_button@x16_lab_button_1_active
\ No newline at end of file
--- source/gamedata.db0/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_2.ltx	2026-10-15 20:03:10.991226300 +0100
+++ patches/x16/gamedata/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_2.ltx	2026-10-15 20:40:04.442320300 +0100
@@ -4,7 +4,8 @@
 [ph_button@x16_lab_button_2_active]
 anim = lab_primary_switcher_idle
 tooltip = st_primary_switcher_idle_off_desc
-on_press = ph_button@x16_lab_button_2_deactivate %=run_cam_effector(fatigue)%
+on_info = {+X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO} ph_button@x16_lab_button_2_done
+on_press = ph_button@x16_lab_button_2_deactivate %=run_cam_effector(fatigue) +X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO%
 
 [ph_button@x16_lab_button_2_deactivate]
 anim = lab_primary_switcher_off
@@ -12,6 +13,12 @@
 
 [ph_idle@system_message_3]
 on_info = %+X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO =play_sound(system_message_3)%
-on_timer = 5000 | ph_idle@nil
+on_timer = 5000 | ph_button@x16_lab_button_2_done
 
-[ph_idle@nil]
\ No newline at end of file
+[ph_button@x16_lab_button_2_done]
+anim = lab_primary_switcher_off
+on_info = {-X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO} ph_button@x16_lab_button_2_active
+
+; kept so saves made with the old logic (active_section = ph_idle@nil) still load
+[ph_idle@nil]
+on_info = {+X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO} ph_button@x16_lab_button_2_done, {-X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO} ph_button@x16_lab_button_2_active
\ No newline at end of file
--- source/gamedata.db0/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_3.ltx	2026-10-15 20:03:10.992257800 +0100
+++ patches/x16/gamedata/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_3.ltx	2026-10-15 20:40:04.442320300 +0100
@@ -4,7 +4,8 @@
 [ph_button@x16_lab_button_3_active]
 anim = lab_primary_switcher_idle
 tooltip = st_primary_switcher_idle_off_desc
-on_press = ph_button@x16_lab_button_3_deactivate %=run_cam_effector(fusker)%
+on_info = {+X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO} ph_button@x16_lab_button_3_done
+on_press = ph_button@x16_lab_button_3_deactivate %=run_cam_effector(fusker) +X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO%
 
 [ph_button@x16_lab_button_3_deactivate]
 anim = lab_primary_switcher_off
@@ -12,7 +13,12 @@
 
 [ph_idle@system_message_4]
 on_info = %+X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO =play_sound(system_message_4)%
-on_timer = 5000 | ph_idle@nil
+on_timer = 5000 | ph_button@x16_lab_button_3_done
 
-[ph_idle@nil]
+[ph_button@x16_lab_button_3_done]
+anim = lab_primary_switcher_off
+on_info = {-X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO} ph_button@x16_lab_button_3_active
 
+; kept so saves made with the old logic (active_section = ph_idle@nil) still load
+[ph_idle@nil]
+on_info = {+X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO} ph_button@x16_lab_button_3_done, {-X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO} ph_button@x16_lab_button_3_active
\ No newline at end of file
--- source/gamedata.db0/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_4.ltx	2026-10-15 20:03:10.992257800 +0100
+++ patches/x16/gamedata/configs/scripts/coop_l08_x16/x16_lab_primary_switcher_4.ltx	2026-10-15 20:40:04.443274800 +0100
@@ -4,14 +4,21 @@
 [ph_button@x16_lab_button_4_active]
 anim = lab_primary_switcher_idle
 tooltip = st_primary_switcher_idle_off_desc
-on_press = ph_button@x16_lab_button_4_deactivate %=run_cam_effector(surge_02)%
+on_info = {+X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO} ph_button@x16_lab_button_4_done
+on_press = ph_button@x16_lab_button_4_deactivate %=run_cam_effector(surge_02) +X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO%
 
 [ph_button@x16_lab_button_4_deactivate]
 anim = lab_primary_switcher_off
 on_timer = 500 | ph_idle@system_message_1 %=turn_off(x16_primari_switcher_hanging_lamp_green_1) =turn_off(x16_primari_switcher_hanging_lamp_green_2) =turn_off(x16_primari_switcher_hanging_lamp_green_3) =play_sound(switch_2)%
 
 [ph_idle@system_message_1]
-on_info = %+X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO =play_sound(system_message_1) =scenario_autosave(st_get_out_of_the_lab)%
-on_timer = 5000 | ph_idle@nil
+on_info = {-X16_LAB_AUTOSAVE_DONE} %+X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO +X16_LAB_AUTOSAVE_DONE =play_sound(system_message_1) =scenario_autosave(st_get_out_of_the_lab)%
+on_timer = 5000 | ph_button@x16_lab_button_4_done
 
+[ph_button@x16_lab_button_4_done]
+anim = lab_primary_switcher_off
+on_info = {-X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO} ph_button@x16_lab_button_4_active
+
+; kept so saves made with the old logic (active_section = ph_idle@nil) still load
 [ph_idle@nil]
+on_info = {+X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO} ph_button@x16_lab_button_4_done, {-X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO} ph_button@x16_lab_button_4_active
\ No newline at end of file
```
