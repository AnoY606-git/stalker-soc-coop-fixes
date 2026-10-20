# Player-count enemy scaling (all levels, server only)

Requested by players via the Shadow of COOP maintainer: more players should mean more and tougher enemies, so 4 players do not
trivialise fights and 1 player is not overwhelmed. 1 player is exactly the original SoC balance.

## How enemies are spawned in this mod (research)
- **Fixed squads.** Almost every squad in `configs/misc/squad_descr_coop_*.ltx` is a hand-made squad: a fixed `npc = a, b, c` list,
  a `target_smart`, a `story_id` (621 of 656 squads have a fixed list; only 35 are `npc_random` + `npc_in_squad`). They are created at
  level start from `[start_position_<level>]` in `configs/misc/simulation.ltx` by `sim_board:fill_start_position`.
- **Every creation goes through `sim_board:create_squad`** (start positions, smart terrain respawn `se_smart_terrain:call_respawn`,
  `xr_effects.create_squad`). It calls `squad:create_npc`, which does `alife():create` for each member (`add_squad_member`).
- **Smart terrains** (`configs/scripts/<level>/smart/*.ltx`): `max_population` counts squads (scripted squads with a `target_smart` are not
  counted, `smart_terrain_squad_count`), `respawn_params` + `spawn_num` respawn a squad some time after it died (`try_respawn`, only when the
  nearest player is > 150 m away). A respawned squad has the same section, so the same `story_id`.
- **Job slots** are the limit. Every NPC of a squad that is assigned to a smart terrain must get a job (`select_npc_job`), jobs are listed in
  `smart.jobs`, most with a time-of-day precondition. No free job = `abort("Insufficient smart_terrain jobs")`, and a job-less NPC reaching
  `setup_logic` is the known `smart_terrain.script:638 job_data nil` crash.
- **Story ids.** A second squad with the same section while the first lives aborts the server (`story_objects_registry:register`:
  "two or more objects with the same story_id"). So an extra squad can never be a second copy of a stock squad section.
- **Players** are counted with `db.mp_actors` (id -> actor object, filled on the server for every connected player), e.g. `coop_map_vote`,
  `sim_squad_scripted:set_squad_relation`. `get_players_count()` is one higher on a dedicated server (the spectator slot).
- The MSO co-op add-on was checked for scaling by player count: no (its squads are fixed too).

## What the patch does
1. **Bigger hostile squads.** In `sim_board:create_squad`, after the base members exist and before the squad is assigned to its smart terrain,
   `player_scaling.on_squad_created` adds `base * (factor - 1)` generic members (cloned from the squad's own generic member sections, so a pack of
   dogs gets more dogs, a bandit gang more bandits). `factor = min(max_factor, 1 + extra_per_player * (players - 1))`; the fraction is
   rounded per squad with a stable hash of the squad id (some squads +1, some not), at most `max_extra_members`.
2. **Follows the player count.** A 1 s tick (`level.add_call`) watches `db.mp_actors`. When the count changes, squads that were created through
   the hook and are currently **offline** are grown (new member registered in the smart terrain) or shrunk (extras released, same pattern as the
   Sarcophagus trim) a few per tick. Online squads are left alone until they go offline.
3. **Reinforcement squads.** Per hostile smart terrain at most `max_extra_squads_per_smart` (1) extra squad, chance
   `extra_squads_per_player * (players - 1)` per smart (stable per smart id). It is a `<section>_ps` copy of one of the smart's hostile
   squads, generated into `configs/misc/squad_descr_pscale.ltx` without `story_id` and `on_death` (see `gen_squads.py`, 402 copies), created
   with `board:create_squad` + `enter_smart` like `xr_effects.create_squad`. Only when every player is >= `reinforce_min_distance` away,
   `reinforce_first_delay_s` after the count changed, and with `reinforce_cooldown_s` after an extra squad died. Removed again (if offline)
   when the player count drops.
4. **Job-slot safety (two layers).**
   - Before adding anything: `free = floor(job_leaves * slot_fraction) - smart.population - slot_margin`; extras are capped by it and a
     reinforcement squad needs `free >= its size`.
   - Net: `smart_terrain.script` (db1 copy, 4 added lines in `select_npc_job`) calls `player_scaling.on_no_job` before the abort. An extra NPC
     without a job is released 1.5 s later instead of crashing; an original NPC without a job releases one extra of that smart and retries on
     the next `update_jobs`. Only if there is no extra to blame does the vanilla abort stay.
5. **Never touched:** friendly/neutral factions (only `hostile_factions` are scaled), any squad with a named member (a member section with
   `story_id`), the Sarcophagus (`skip_levels`), the original squads' own members, story flags and `on_death`.

## Tunables: `gamedata/configs/player_scaling.ltx`
`enabled`, `human_extra_per_player`, `mutant_extra_per_player` (0.5 = +50% squad size per extra player: 2 players 1.5x, 3 players 2x, 4 players
2.5x), `max_factor`, `max_extra_members`, `extra_squads_per_player`, `max_extra_squads_per_smart` (do not raise above 1), `reinforce_*`,
`slot_fraction` / `slot_margin`, `hostile_factions`, `skip_levels`, `skip_smarts`, `log`. Defaults are read when the server starts. The log
is `pscale.log` in the game's logs folder.

## Files
- `gamedata/scripts/player_scaling.script`: everything above (config, player count, members, rebalance, reinforcement, census).
- `gamedata/scripts/sim_board.script`: db1 file + 2 lines in `create_squad` (the hook).
- `gamedata/scripts/smart_terrain.script`: db1 file + 4 lines in `select_npc_job` (the net). **Another patch that also replaces
  `sim_board.script` or `smart_terrain.script` conflicts with this one**; merge the hook lines.
- `gamedata/configs/player_scaling.ltx`: the tunables.
- `gamedata/configs/misc/squad_descr.ltx`: db0 file + `#include "squad_descr_pscale.ltx"`.
- `gamedata/configs/misc/squad_descr_pscale.ltx`: generated by `gen_squads.py <source dir>` (re-run it if squad descriptions change).

## Not done / limits
- Enemy health and accuracy are not scaled (no clean engine hook: health is capped at 1.0, damage would need a `hit_callback` in
  `bind_stalker`/`bind_monster`). More enemies only.
- Tracking is in memory. After loading a save, squads created before the load are no longer rescaled when the player count changes
  (they keep their size); newly created and respawned squads scale normally. A new game is recommended anyway.
- Only squads created through `sim_board:create_squad` are scaled. Online squads change size only after they go offline.
- `slot_fraction` is a guess for "how many of a smart terrain's jobs exist at any hour"; the net layer covers a wrong guess.
- Roaming `npc_random` squads without a smart terrain get extras only at creation.

## Tests (real game, xrMPE 0.9, test addon built inside a slot lease and deleted afterwards)
Hostile member counts are the census over every smart terrain the server has loaded (all levels), so they are the same kind of number in every phase.
- **coop_l01_escape, listen, forced player count 1 -> 2 -> 4 -> 1** (`run_coop`-style harness, hook forces `player_scaling.test_count`):
  PASS more enemies with 4 players: 326 (1p) -> 476 (2p) -> 715 (4p), 9 reinforcement squads; PASS 2p is between 1p and 4p;
  PASS back to 1 player shrinks to 326 (reinforcements removed, extras released). RESULT: PASS, no crash over about 5 minutes, 0 "no job" lines, no errors in `pscale.log`.
- **coop_l02_garbage, same scenario:** 337 -> 492 -> 746 (17 reinforcement squads) -> 337. RESULT: PASS, 0 "no job" lines.
- **Real 2 clients (dedicated server, `run_coop.ps1 -Clients 2 -Mode dedicated`, coop_l01_escape):** the server counted 2 players from `db.mp_actors`
  (`player count 0 -> 2`); PASS pscale_real_player_count_is_2; census with 2 real players 500 hostile members vs 340 with the count forced to 1 in the same world:
  PASS pscale_real_2_players_more_than_1. RESULT: PASS (clients A and B spawned, shared state equal, no FATAL in any log).
- In listen mode `mp_actors` and `get_players_count()` both report 1 per local player; the second client of a listen server collapses into the host on one PC (harness limit, not a patch issue).
Not tested: real play of the fights (enemy behaviour of the added members), save/load, more than 2 real clients at once.

## Rule and Sarcophagus (2026-10-19, static check, untested)
- The rule is already +0.5x per extra player for humans AND mutants (`human_extra_per_player = mutant_extra_per_player = 0.5`, `max_factor = 2.5`):
  1 player 1.0x, 2 players 1.5x, 3 players 2.0x, 4 players 2.5x. Change the two numbers in `player_scaling.ltx` to tune them separately.
- Scaled: every squad made through `sim_board:create_squad` (start squads, restrictor `create_squad`, smart respawns) whose faction is in `hostile_factions`
  (all `monster*` factions included) and whose members have no `story_id`. Not scaled: mutants placed directly in a level spawn without a squad, the
  Bar arena dog waves (`defence_arena.script`, unused test code), squads with named members, and anything beyond the smart terrain's free job slots.
- The Sarcophagus (`coop_l11_sarcofag`) is in `skip_levels`, so it is never multiplied (1.0x for any player count), below the requested limit of about +0.5x per extra player.



## Review of the save/load rescale fix (2026-10-19, static, untested)
Read `persistence` / `restore()` once against `story_flags`, `game_sv.save/load` and `sim_board`. The flag name parse (`PSC_<squad>_<check>_<base>_<extra ids>`),
the stale-flag clean-up, the use of `story_flags.story_flags` (the module's own table, replaced by `reset_flags()` but always read fresh) and the
15 s restore delay are consistent. One real problem found and fixed: **every true story flag goes into one reliable packet** (`game_sv.SendStoryFlags`,
sent to each joining client, `net_packet` limit 16 KB) and the one-flag-per-squad scheme adds about 20 to 40 bytes per scaled squad, which on a
level with a few hundred hostile squads could push that packet over the limit when a player joins. `save_info` / `drop_info` / `restore` now keep a byte
budget (`MAX_FLAG_BYTES = 10000`); squads beyond it are not persisted (they keep their size after a load, as before the fix). Nothing else changed.
Not tested: save, load, join with the budget active.

## Кратко (RU)
Проверено сохранение/загрузка масштабирования. Найден риск: все флаги истории уходят одним пакетом новому игроку, по флагу на отряд; добавлен лимит
10000 байт. Не проверено в игре.
