# Task guard - notes

## Problem
`xr_effects.give_task` on the server hands the task to the first player in `db.mp_actors`. When no player is spawned
(everyone dead and respawning, or still loading after a level change) it falls through to `getLocalActor():get_task()`,
which is nil on a dedicated server, and the server crashes:
`xr_effects.script:1686: attempt to index a nil value`. Seen in our automated runs on Cordon when a quest restrictor fired
before the player spawned.

## Fix
- `gamedata/scripts/coop_task_guard.script`: keeps such tasks and gives them once a player exists (runs from
  `client_tasks.update_delayed_tasks`, which the server actor binder calls every update).
- The wrapper of `give_task` is appended to `patches/cnpp_shake/gamedata/scripts/xr_effects.dscript` (only one patch can ship
  that file). Listen servers are unchanged (they have a local actor).

## Кратко (RU)
Выдача задания на выделенном сервере, когда ни один игрок не заспавнен, роняла сервер (xr_effects.script:1686). Теперь задание откладывается и выдаётся, как только появится игрок.
