# cordon_bridge: the soldiers at the Cordon railway bridge as in Shadow of Chernobyl

## What the original game does (SoC `esc_bridge`)
Six posts under the railway bridge: five soldiers and Major Kuznetsov (post 2). They ignore the player (`combat_ignore_cond =
{-ESC_BRIDGE_PASS_FIRE =fighting_actor}`) until the player shoots one of them (`hit@soldier`: `{=hit_by_actor} %+ESC_BRIDGE_PASS_FIRE%`) or kills
one (`death@soldier`: `{=killed_by_actor}`); then all of them fire. The mod has the bridge zone restrictor on top (same place as the SoC `esc_bridge_kill_zone`).

## What the mod had
Shadow of COOP 8.x had 4 soldiers + Kuznetsov (5 NPCs), all four soldiers on the railway DECK (y about 20, 17 m above the SoC posts), the zone
trigger (`esc_the_order_to_attack_the_players_space_restrictor`, any player, patch `any_player_restrictors`) and the neutral/attack sections, but
**no hit trigger**: a player could shoot a soldier and nothing changed unless a whole squad died. Major Shtirts is defined (character, squad,
walker file) but switched off in the mod itself (job and simulation line commented out); SoC has no Shtirts. He stays off.

## Changes (this patch)
| File | Change |
|---|---|
| `configs\misc\squad_descr_coop_l01_escape.ltx` | squad `esc_smart_terrain_7_military_4_squad` has two soldiers (`npc = sim_default_military_0, sim_default_military_0`). Nothing else. |
| `configs\scripts\coop_l01_escape\smart\esc_smart_terrain_7.ltx` | new job `esc_smart_terrain_7_walker_army_5`. `max_population` stays 3 (see decisions). |
| `configs\scripts\coop_l01_escape\esc_smart_terrain_7_walker_army.ltx` | jobs army_1..5: SoC stance `guard`, `on_hit` and `on_death` in the `[logic@...]` section, new sections `[hit@esc_bridge_soldier]` and `[death@esc_bridge_soldier]`. Neutral/attack sections, squad-death switches and `meet = no_meet` as in the mod. |
| `configs\scripts\coop_l01_escape\esc_smart_terrain_7_walker_kuznetsov.ltx` | Kuznetsov gets the same `on_hit` / `on_death` rules. His dialogs, vodka quest and `meet@hello_players` are untouched. |
| `gamedata\spawns\all.spawn` | NOT in this folder: the shipped copy is `patches\darkvalley_restore\gamedata\spawns\all.spawn` (one patch per file). `tools\make_paths.py` changed it: chunk 3 only, 10 patrol paths (8 changed, 2 new `walker_5_walk` / `walker_5_look`). |
| `tools\` | `gen_configs.py` (makes the four config files from the mod sources), `make_paths.py` (all.spawn, with `--check` and `--verify`), `check_bridge.py` (config/path consistency, seconds). |
| `tests\bridge_hooks.lua` | live console probes, one command per test (test plan below). Never shipped. |

### Counts before / after
| | before | after |
|---|---|---|
| army soldiers (generic `sim_default_military_0`) | 4 (4 squads of 1) | 5 (squads 1 to 3 of 1, squad 4 of 2) |
| Kuznetsov | 1 | 1 |
| NPCs at the bridge | 5 | 6 = SoC posts 1 to 6 |
| jobs in `esc_smart_terrain_7.ltx` | 4 + Kuznetsov | 5 + Kuznetsov |
| walk paths | 4, all on the deck (y 19.9 to 20.1) | 5 at the SoC posts (y 2.3 to 3.2) + Kuznetsov's old path (5 m from SoC post 2) |
| patrol paths in all.spawn | 3182 | 3184 (+2 new, 8 rewritten), file +58 bytes |
| squads / story ids / flags | 6 defined (Shtirts off) | the same, no new id, no new flag |

SoC posts used (Steam SoC all.spawn, same Cordon coordinates): post1 (45.5, 2.7, 142.0), post3 (63.0, 3.2, 171.7), post4 (47.8, 2.7, 174.2),
post5 patrols (71.5, 2.8, 135.7) <-> (70.9, 2.8, 168.4) waiting 5 s at each end, post6 (51.4, 2.3, 178.9); post2 = Kuznetsov (59.5, 1.9, 130.9).
Look points are the SoC ones (flags 1/2 pair the look point with its walk point).

### Decisions
* **5th soldier = a second member of squad 4, not a 5th squad.** A new squad would need a `simulation.ltx` line (owned by `sarcophagus_count`),
  a new `..._SQUAD_DEAD` flag (story_flags_table) and a new story id. Squads only matter for spawning and for the `..._DEAD` flags: the jobs
  (`suitable = check_npc_name(sim_default_military_0)`) are not tied to a squad, so any soldier takes any free post (5 jobs, 5 soldiers). The
  `DEAD_4` switch now fires when both members are dead, the hit/kill rules cover the rest.
* **`max_population` is not changed** (the earlier draft set 6). It limits how many *simulation* squads may move into the smart terrain
  (`target_precondition`); the bridge squads have a `target_smart` and are not counted, so a bigger number would let roaming squads in.
* **`on_hit` / `on_death` belong in `[logic@...]`.** `xr_logic.configure_schemes` reads the generic schemes (hit, death, combat) only from the job
  section, never from `[walker@...]`; the earlier draft had `on_hit` in the walker sections, where the engine never looks (the Freedom fix in
  `freedom_duty` puts it in the logic section as well).
* **Player-only triggers.** `hit_by_actor` / `killed_by_actor` are the xrMPE conditions (`xr_conditions.script`, `is_object_actor_by_id`): true for
  EVERY player actor (host or client), false for mutants and NPCs. The rule is once only (`-ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO`) and makes
  the same autosave as the restrictor.
* The zone box in all.spawn is unchanged (56.9 0.6 157.1, 32.3 x 35.6 x 42.4 m, y -17.2 to 18.4). The soldiers no longer stand on the deck, so
  there was no reason to move it. (An earlier draft raised it; that edit is gone, chunk 1 is byte for byte the original.)
* Squad-death switches (`ESC_SMART_TERRAIN_7_MILITARY_n_SQUAD_DEAD`) stay as the mod has them: they fire when a whole squad is dead, whoever killed it.
* Combat: the mod's `combat_ignore_cond = true` (soldiers ignore everybody, mutants included) is kept. SoC ignored only the player.

## How neutrality and the trigger work
1. Start: every soldier runs `walker@esc_smart_terrain_7_walker_army_N` with `combat_ignore_cond = true`, `combat_ignore_keep_when_attacked = true`,
   `meet = no_meet`: they stand at their post and neither shoot nor talk (Kuznetsov talks).
2. The order is the story flag `ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO`. Story flags are shared by all players, synced and written into the
   savegame (`story_flags.save_flags`), so the hostility survives save/load.
3. It is given by one of: a player entering the zone (`on_any_player_inside`, unless the vodka quest is taken: Kuznetsov's pass), a player hit on any
   soldier or Kuznetsov (`hit@esc_bridge_soldier`, server side, any player), a player kill (`death@esc_bridge_soldier`), or the death of a whole bridge squad.
4. Every `walker@..._N` section has `on_info = {+FLAG} walker@..._N_attack_players` (and the six squad-death flags); the section switch happens on the
   NPC's next update (about 1 s). The attack sections have `combat_ignore_cond = false`, so the soldiers fight any player they see.

## Offline checks (done)
```
python patches\cordon_bridge\tools\check_bridge.py                       -> 0 problem(s)
python patches\cordon_bridge\tools\make_paths.py <all.spawn> - --ai <Cordon level.ai> --verify <original all.spawn>
      -> chunks 0, 1, 2, 4 identical, chunk 3: 10 changed/new paths, 3174 identical, VERIFY PASS; 16 path points valid (level vertex on the mesh,
         game vertex = cross table, on the Cordon level)
python tools\check_conflicts.py soc_levels weapon_upgrades npc_attachments arrival_facing inventory_carry   -> only the 8 documented overlaps
python tools\check_lua_escapes.py                                         -> no hit in this patch
python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry   -> BUDGET OK
```
Regenerate: `python tools\gen_configs.py <Shadow of COOP 8.0\source\gamedata.db0\configs> gamedata\configs`;
`python tools\make_paths.py <original all.spawn> <new all.spawn> --ai <Cordon level.ai>` (idempotent). If `darkvalley_restore`'s all.spawn is ever
regenerated, run make_paths.py on it again. If `soc_levels` (Akasi's Cordon) is revived, run make_paths.py with ITS level.ai after its swap.

## TEST PLAN (live console, one session at a time)
Stage: `python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry --stage=<out>\stage`, then copy
`<out>\stage\gamedata\{configs,scripts,spawns,levels,meshes,sounds}` (no textures, about 70 MB) to `<lite>\gamedata`.
Session start (every session below is a FRESH game, no `-Save`: the saved worlds were made with the old all.spawn):
```
cd <games>\tools\stalker_xrmpe\live
powershell -NoProfile -ExecutionPolicy Bypass -File start_live.ps1 -Map coop_l01_escape -Owner <you> -Name br -Clients 2 -ExtraDir <lite>\gamedata -Hooks <repo>\patches\cordon_bridge\tests\bridge_hooks.lua
powershell -NoProfile -ExecutionPolicy Bypass -File lua.ps1 -Name br "coop_scenes.status()"       (repeat until it says active=nil; the intro puts players back in the bunker)
```
`L` below = `powershell -NoProfile -ExecutionPolicy Bypass -File lua.ps1 -Name br [-Timeout N] "<lua>"`. Stop with `stop_live.ps1 -Name br`.
Every test prints one first line `PASS bp.t_x: ...` or `FAIL bp.t_x: ...`. `bp.help()` lists them. `bp.report()` shows every soldier at any time.

**Session A (dedicated, 2 clients): count, posts, neutrality, non-player hits, hit by client B, save/load**
| # | Command | Expected |
|---|---|---|
| A1 | `L "bp.go('safe')"`, then wait 30 s | `2 player(s) moved to (59.x, 1.x, 127.x)`; soldiers come online |
| A2 | `L "bp.t_soldiers()"` | `PASS bp.t_soldiers: 5 soldiers + 1 Kuznetsov alive, 5 of 5 posts matched, 6 online, jobs held 5` and 6 lines (squads 1 to 3 once, squad 4 twice, Kuznetsov) |
| A3 | `L -Timeout 150 "bp.t_neutral(60)"` | after 60 s: `PASS bp.t_neutral: player stood 60 s next to Kuznetsov outside the zone; flag=false hurt_frames=0 hostile_max=0 engaged_max=0 online=6` (player within 4 to 9 m of Kuznetsov and soldier 4a, nobody attacks, no flag) |
| A4 | `L -Timeout 60 "bp.t_nohit()"` | `PASS bp.t_nohit: a mutant (dog_weak) and an NPC (bandit) each hit soldier #<id> (...); flag=false hostile_sections=0` |
| A5 | `L -Timeout 90 "bp.t_hit('qaB')"` | client B (not the first player) hits one soldier once: `PASS bp.t_hit: player qaB hit soldier #<id> (squad ...) once with 5% damage -> flag after <=1 s, 6 of 6 online army NPCs hostile after <=10 s, engaging players: [...]` |
| A6 | `L "bp.t_save()"`, wait 5 s, `L "live.load_last()"`, wait until `L "live.state()"` answers on coop_l01_escape, `L "bp.god_on()"`, `L -Timeout 150 "bp.t_load()"` | `PASS bp.t_save: flag set and 6 of 6 online army NPCs hostile; save requested`, then `PASS bp.t_load: after load: flag=true, 6 of 6 online army NPCs hostile (0 dead)` |
FAIL reading: `flag after ... NOT given` = the hit callback did not reach the rule (check the server log for `hit by [qaB]` and `_bp: hit_by_actor`); `N still neutral`
= flag given but a walker did not switch; `flag LOST by the load` = story flag not saved.

**Session B (fresh, dedicated): the zone.** After the intro: `L -Timeout 180 "bp.t_zone()"` -> the players stand 8 s outside (still neutral), are teleported into the zone, and
`PASS bp.t_zone: players teleported into the zone (engine inside-test: ...) -> flag after <=2 s, 6 of 6 online army NPCs hostile ...`.

**Session C (fresh): kill without a hit (death scheme alone).** `L "bp.go('safe')"`, wait 30 s, `L -Timeout 150 "bp.t_kill('qaB')"` -> `PASS bp.t_kill: player qaB killed soldier #<id> of
squad 4 (2 members, no hit) -> flag after ...`. The victim is a member of the two man squad, so the squad-death switch cannot be the reason. (First use of `on_death` in this mod: if this
fails with the flag not given while A5 passes, drop the `on_death` lines from the army and Kuznetsov logic sections and the `[death@...]` sections; the squad-death switches still cover kills.)

**Session D (fresh): Kuznetsov's pass.** `L "bp.go('safe')"`, wait 30 s (the zone is online), `L "bp.give_vodka()"` (true), wait 5 s (the zone switches itself off), `L "bp.go('inside')"`,
wait 30 s, `L "bp.report()"` -> `FLAG=false`, `hostile_section=0` (the vodka quest is the pass, as in SoC). Then `L -Timeout 90 "bp.t_hit('qaA')"` -> PASS (the hit rule still works under the pass).

**Session E (optional, `start_live.ps1 ... -Mode listen`): host vs client.** Same as A5 once with `bp.t_hit('qaB')` (client) and once, fresh, with `bp.t_hit('qaA')` (host).

Notes for the tester: the tests apply the hit/kill from the server with the player as attacker (the same callback a real bullet reaches). `bp.god_on()` keeps the players
alive while the soldiers shoot; `bp.go('far')` leaves them behind. A hostile test cannot be undone: restart the session for the next one.

## Кратко по-русски
Военные у железнодорожного моста на Кордоне приведены к оригиналу SoC: 5 солдат + майор Кузнецов на 6 постах SoC (раньше 4 солдата, все на мосту на высоте 20 м).
Пятый солдат: второй боец в отряде 4 (новый отряд потребовал бы правок `simulation.ltx` и таблицы флагов). Все нейтральны к игрокам, пока ЛЮБОЙ игрок не
выстрелит в одного из них, не убьёт кого-то или не войдёт в зону моста (кроме случая, когда взят квест с водкой для Кузнецова: это пропуск, как в SoC);
тогда флаг `ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO` (общий, сохраняется в сохранении) делает всех враждебными. Попадания мутантов и NPC флаг не дают.
Пути патрулей лежат в `darkvalley_restore\gamedata\spawns\all.spawn` (меняется только блок 3, остальное побайтно как было). План проверки в игре выше.
