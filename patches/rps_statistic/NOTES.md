# rps_statistic - notes

## Problem
`bind_stalker.script` (Shadow of COOP 8.0, `mp_actor_binder:update_rps_game`) calls `xr_statistic.inc_rps_games_won(id)` when one
player wins the rock-paper-scissors gesture game against another player within 5 m. The base xrMPE `xr_statistic.script` has no such
function (only the Call of Pripyat add-on's copy has it), so the call is `attempt to call field 'inc_rps_games_won' (a nil value)`,
which is a FATAL ERROR in this engine and closes the game. Seen in a player's crash dump (breakpoint exception, script
`gamedataind_stalker.script`, field `inc_rps_games_won`). It is the only `xr_statistic.*` function the mod calls that the base lacks
(checked over the mod's scripts and all patches).

## Fix
`gamedata/scripts/xr_statistic.dscript`: appended to the base `xr_statistic.script`; defines `inc_rps_games_won(id)`. The counter is
not saved and not sent, so the save format and the network packets of `xr_statistic` stay the same (no mismatch between players
with and without this patch).

## Test
`tools\stalker_xrmpeun_coop.ps1`, Cordon, dedicated server + 1 client, hook `rps_hooks.lua` (test only): client A moves next to a Cordon NPC that
stands in for the second player (listed in `db.mp_actors`), gestures A = rock, stand-in = scissors, so the real
`bind_stalker.mp_actor_binder:update_rps_game` runs. (A real second client did not spawn in time on the loaded PC.)
- Without the patch: `RESULT: FAIL ... client A CRASH`, log: `FATAL ERROR ... bind_stalker.script:242: attempt to call field 'inc_rps_games_won' (a nil value)`
  (`type(xr_statistic.inc_rps_games_won)` = nil).
- With the patch, run 1: `assert A: PASS rps: win counted by update_rps_game stand-in esc_smart_terrain_1_stalker_wolf9970`, `RESULT: PASS`.
- With the patch, run 2: `assert A: PASS rps: win counted by update_rps_game stand-in esc_rookie_technician13192`, `RESULT: PASS`.

## Кратко (RU)
Игра «камень-ножницы-бумага» (жесты двух игроков рядом) вызывала `xr_statistic.inc_rps_games_won`, которой нет в базовом
`xr_statistic.script`: фатальная ошибка скрипта, игра закрывалась. Добавлена функция (счётчик не сохраняется и не передаётся).
