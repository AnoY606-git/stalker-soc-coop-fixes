# Repeatable side quests - notes

## Problem
The original SoC task manager re-offers its finite pool of jobs (artifacts, monster parts such as dog tails, kill stalker / mutants) every 24 game
hours (`idle_time`). Shadow of COOP's equivalents (Sidorovich, Barman, Sakharov, Kruglov, Hunter: 30 "sq" quests) are one-shot: the accept dialog is
gated by a story flag nothing clears, and the quest restrictor that gives the task / spawns the target squad runs once and parks in `sr_idle@nil`.
Details and file:line evidence: Downloads\SoC_COOP_quests\QUESTS.md.

## Fix
New files only; no shared script or dialog XML is edited.
- `gamedata/scripts/coop_repeat_quests.script`: server-side state machine over story flags (saved + synced, so save/load and late join work).
  Quest finished -> flag `RQ_<TASK>_R<game minute>`; when due and the players are on that level the accept/done/fail flags are cleared and
  `RQ_<TASK>_C<n>` bumped, so the unchanged dialogs offer it again. Cycle >= 1: the script re-does what the restrictor did (create_squad if the
  story squad is dead, give_task to all players), `RQ_<TASK>_A<n>` prevents duplicates.
- `gamedata/configs/misc/coop_repeat_quests.ltx`: 26 quests (accept/done/fail flags, squads), `cooldown_min = 1440` (24 game hours, as original).
- `gamedata/scripts/client_tasks.dscript`: appended to client_tasks.script; wraps `update_delayed_tasks` (called every server actor update) to tick the script.
Excluded (cannot be repeated): Bar/Yantar `killer_mutants_1/2` (pre-placed squads, no spawn), Bar `killer_mutants_3` (its chimera smart is on Yantar).

## Multiplayer model
Unchanged: task is shared by all players, each client pays its own `reward_money` once; item hand-in by the talking player. Server-authoritative
(`OnServer()` only). New actor ids get running repeatable tasks (late join).

## Not restored
Duty/Freedom/Wolf/etc. pools and `eliminate_lager`/`defend_lager`/`find_item` types: they depend on camp populations and gulag state the mod does not have.

## Multiplayer risks / confidence
- Reset waits until the players are on the quest's level; the game-time cooldown keeps running meanwhile.
- If .dscript appending is changed by a future xrMPE, ship client_tasks.script instead.

## Test (real game, Cordon, listen server, test bot, cooldown shortened to 2 game minutes in the test build only)
All PASS: dog-tail quest accepted (restrictor gives task, cycle 0) -> 10 dog tails handed in -> reward 2000 paid once, task closed ->
still locked before cooldown -> after forwarding game time the accept/done flags are cleared and cycle 1 starts -> accepted again, script re-gives the task
-> turned in again, 2000 paid exactly once more. Late-join catch-up fired for a forgotten actor id. Kill quest (mutant dogs): cycle 0 spawns the squad,
squad death completes it, after the cooldown it is offered again, cycle 1 gives the task and re-creates the squad.
Not tested: two real players (late join was simulated by forgetting the actor id), Bar/Yantar quests (same data pattern, generated from the same files).
