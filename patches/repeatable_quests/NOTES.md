# Repeatable side quests - notes

## Problem
The original SoC task manager re-offers its finite pool of jobs (artifacts, monster parts such as dog tails, kill stalker / mutants) every 24 game
hours (`idle_time`). Shadow of COOP's equivalents (Sidorovich, Barman, Sakharov, Kruglov, Hunter: 30 "sq" quests) are one-shot: the accept dialog is
gated by a story flag nothing clears, and the quest restrictor that gives the task / spawns the target squad runs once and parks in `sr_idle@nil`.
Details and file:line evidence: Downloads\SoC_COOP_quests\QUESTS.md.

## Fix
(v1.4: the 26 legacy sq_* quests described below were removed with the level maker's task menu, and the 8 legacy kill jobs with them; see "v1.4: fetch jobs ..." at the end. The generated jobs below are the repeatable quests.)
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

## Text and languages
All player-visible text of this patch is string ids (dialog phrases, PDA task titles and descriptions, map spot labels); no script or ltx
holds literal text. The ids live in `configs/text/eng/st_coop_repeat_quests.xml` and `configs/text/rus/st_coop_repeat_quests.xml` (201 ids,
identical id sets, cp1251). Earlier builds shipped the English file as the Russian one, so Russian players saw English dialog lines and task
names. The Russian file is now real SoC-style Russian: Sidorovich, Wolf, Barman, Duty and Saharov each speak in their own voice, the
option prefixes follow SoC's task types ("Уничтожение лагеря", "Защита лагеря", "Найти предмет", "Убить"), and task names such as
"Уничтожить лагерь бандитов" use SoC's wording. Reward numbers and map hints are unchanged. The engine loads every xml in
`configs/text/<language>/` by itself, so no registration is needed. Other languages fall back to the id; add a file under
`configs/text/<lang>/` to cover them.

Checked at the same time (no change needed): `mutant_loot`, `money_transfer`, `cordon_technician`, `player_scaling`, `task_guard`,
`stash_markers` and the cutscene packages route all text through `game.translate_string` and ship real eng + rus files.

How the game language is chosen in xrMPE 0.9: the registry value `HKCU\Software\X-Ray Multiplayer Extension\InstallLang` (eng/rus/ukr)
mounts `game\localization\<lang>.db`; a `configs\localization.ltx` inside an addon is ignored. To test Russian, set that value to `rus`
only while the client starts (it is read at file system init, a few seconds), then set it back.

## Where the targets spawn (site)
Bug report (FOSTER, v1.3): the bandit job from Izya Skamarokh spawned its targets at Arnie's arena inside the Bar; the Bar stalkers and Duty
killed them at once and the map spot was inside the Bar. Cause: every generated job created its squad inside one fixed smart terrain
(`smart =` in `coop_repeat_quests.ltx`), and on the Bar level (and for human targets everywhere) those smart terrains are the inhabited
ones: 13 m or less from the neighbouring Bar/Duty smart terrains, inside the no-weapon / light zones, with their own squads and animation
jobs; two squads in one smart terrain also overflow its job slots (known server crash).

Fix: every generated job now has `site = x, y, z, level vertex id, game vertex id` (a node of the level's AI map).
`coop_repeat_quests.script` creates the squads (or the item) there (`create_squad_at`, same steps as `sim_board:create_squad`, but the squad is
assigned to no smart terrain, so it stays where it was created, never walks into a base and cannot overflow a job slot). `smart =` is only the
fallback if the site cannot be read (a single number in `site` is still read as a game graph vertex id).
Site rules (tool: scratchpad `pick_sites2.py` / `finalize_sites.py`, data: all.spawn objects, the levels' `level.ai` and game graph): a node of
the AI map's main walkable component (islands, roofs and the unreachable corners are out), at least 85 m from every inhabited smart terrain (humans,
zombies), at least 60 m from no-weapon / light zones, at least 80 m from level exits (not for mutant dens), and at least 25 to 45 m from every anomaly /
mine / radiation field object (`zone_*`, centre distance; most sites are 45 to 100 m away); mutant jobs stay within 80 m of their den.
The Bar level is almost one big anomaly field: only four open spots survive the anomaly rule, so the Bar jobs share them by target faction
(bandits, mercenaries, freedom + stalkers, Duty, the dog den, the boar / flesh den; finds on the freedom and merc spots). Two jobs of
hostile factions that are active at the same time can therefore meet there (the spots are 50 to 300 m apart).
Kill and camp jobs: completion is unchanged (SoC: the job ends when the targets are dead, whoever killed them; the 48 game hours timeout
fails it). Defend jobs: the raiders wait at their site (95 to 300 m from the camp) and do not march to the camp; hand-in jobs: the item lies
at the site.

Audit of all 28 generated jobs ("inhabited" = smart terrain with named NPCs or squads; for the defend jobs the defended camp, and for
`rq_sid_camp` the bandit camp it belongs to, are left out of the "nearest inhabited" column; old spawns were 6 to 28 m from inhabited Bar
smart terrains, 57 m from the Cordon army post):

| job | targets | old spawn | new site (x y z) | nearest inhabited smart | nearest anomaly zone | nearest no-weapon / light zone | from the giver |
|---|---|---|---|---|---|---|---|
| rq_sid_camp | camp (2 bandit squads) | esc_smart_terrain_12 | 97 13 612 | 301 m | 62 m | 936 m | 817 m |
| rq_sid_kill | kill (bandit patrol) | esc_smart_terrain_10 | -125 -26 -468 | 119 m | 56 m | 356 m | 331 m |
| rq_sid_defend | defend (raiders near village) | esc_smart_terrain_1 | -265 -12 -252 | 149 m | 67 m | 119 m | 121 m |
| rq_wolf_camp1 | camp (2 bandit squads) | esc_smart_terrain_9 | -181 32 192 | 225 m | 87 m | 333 m | 340 m |
| rq_wolf_camp2 | camp (2 dog squads) | esc_smart_terrain_4_m | -60 0 216 | 148 m | 46 m | 398 m | 391 m |
| rq_shu_find | find (Fort pistol) | esc_smart_terrain_5 | -71 -23 -251 | 132 m | 64 m | 212 m | 169 m |
| rq_bar_kill1 | kill (merc novice) | bar_smart_terrain_7 | 23 5 360 | 232 m | 76 m | 301 m | 319 m |
| rq_bar_kill2 | kill (bandits advanced) | bar_smart_terrain_11 | -25 1 325 | 219 m | 71 m | 286 m | 307 m |
| rq_ska_kill | kill (bandit novice, Izya) | bar_smart_terrain_6 | -25 1 325 | 219 m | 71 m | 286 m | 307 m |
| rq_vor_kill | kill (freedom scouts) | bar_smart_terrain_11 | 76 3 337 | 199 m | 66 m | 255 m | 282 m |
| rq_pet_kill | kill (merc advanced) | bar_smart_terrain_6 | 23 5 360 | 232 m | 76 m | 301 m | 319 m |
| rq_inf_kill | kill (renegade stalkers) | bar_smart_terrain_9 | 76 3 337 | 199 m | 66 m | 255 m | 282 m |
| rq_vor_camp1 | camp (2 bandit adv squads) | bar_smart_terrain_12 | -25 1 325 | 219 m | 71 m | 286 m | 307 m |
| rq_vor_camp2 | camp (2 freedom squads) | bar_smart_terrain_13 | 76 3 337 | 199 m | 66 m | 255 m | 282 m |
| rq_vor_camp3 | camp (2 merc squads) | bar_smart_terrain_14 | 23 5 360 | 232 m | 76 m | 301 m | 319 m |
| rq_inf_camp | camp (2 duty squads) | bar_smart_terrain_13 | 239 4 -156 | 146 m | 26 m | 209 m | 242 m |
| rq_bar_camp1 | camp (2 dog squads) | bar_smart_terrain_1_m | 191 4 -144 | 135 m | 55 m | 177 m | 213 m |
| rq_bar_camp2 | camp (boar + flesh) | bar_smart_terrain_2_m | 3 -0 239 | 134 m | 32 m | 198 m | 220 m |
| rq_hun_camp | camp (flesh + boar) | bar_smart_terrain_2_m | 3 -0 239 | 134 m | 32 m | 198 m | 220 m |
| rq_bar_defend | defend (bandits at camp near Bar) | bar_smart_terrain_8 | -25 1 325 | 219 m | 71 m | 286 m | 307 m |
| rq_inf_defend | defend (duty raid on Freedom camp) | bar_smart_terrain_8 | 239 4 -156 | 146 m | 26 m | 209 m | 242 m |
| rq_vor_defend | defend (bandits at Duty post) | bar_smart_terrain_4 | -25 1 325 | 219 m | 71 m | 286 m | 307 m |
| rq_vor_find | find (AKS-74U) | bar_smart_terrain_10 | 23 5 360 | 232 m | 76 m | 301 m | 319 m |
| rq_inf_find | find (Desert Eagle) | bar_smart_terrain_10 | 76 3 337 | 199 m | 66 m | 255 m | 282 m |
| rq_zho_find | find (vodka) | bar_smart_terrain_7 | 76 3 337 | 199 m | 66 m | 255 m | 282 m |
| rq_sak_camp1 | camp (snorks) | yan_smart_terrain_3_m | -132 -19 -98 | 96 m | 178 m | 237 m | 244 m |
| rq_sak_camp2 | camp (bloodsucker) | yan_smart_terrain_5_m | 286 6 -292 | 200 m | 287 m | 257 m | 252 m |
| rq_sak_find | find (detector) | yan_smart_terrain_6_z | 144 6 24 | 85 m | 260 m | 318 m | 320 m |

The 8 legacy kill jobs of the mod itself (`esc_start_sq_killer_*`, `*_mutants_*`) are unchanged: their squads are the mod's own residents at
their own smart terrains (cycle 1 and later re-create the same squad there), as in the original quests; the 18 art / part jobs spawn nothing.

Tests (listen server, test bots in `tests/`; the Bar run starts on Cordon and travels by party vote, the Bar's alife only comes online that way):
- `rq_spawn_hooks.lua`, Izya's job (first site, vertex 1224): targets at the site, 0.0 m; nearest NPC 214 m; map spot on the squad; the player
  moved next to them: 2 of 2 online and alive, still alive after 60 s.
- `batch_esc.lua` / `batch_bar.lua` / `batch_yan.lua` (generated by `gen_batch.py` from the sites; one per level): accepts every generated job of
  the level one after another and checks per job: targets / item spawned at the site, map spot, no other NPC within 80 m, no anomaly zone within
  15 m, y sane vs the site on the server and again when the targets come online (nothing below / inside geometry), alive 30 s after the player
  arrived. Cordon (6 jobs): the first run failed `rq_sid_camp` (site y = 34 on a hillside: the squad stood 18 m off the vertex height online) and two jobs lost their targets only
  because the bandits killed the test player (god mode was not on; the batch now sets `g_god`). The site was replaced by a flat one near the bandit camp (97 13 612); second run:
  41 of 42 checks PASS, the remaining failure was again `rq_sid_camp` y (8.2 m).
  Bar batch (19 jobs, final sites, Cordon start + vote): 131 PASS, 2 FAIL out of 133 checks (`rq_bar_kill1` y 4.3 m, `rq_hun_camp` spread 6.3 m).
  Yantar did not run then (display driver reset).

Final re-check (2026-10-21, fresh boot of the PC). What the old failures turned out to be, and the rule that replaces the old checks. The old batch
measured the targets 5 to 6 s after they came online, when they had already walked away (and the camp targets are chasing the player), so a hillside
or an animal pack wandering looked like a bad site. The batches (`batch_esc/bar/yan.lua`) now measure at the moment that matters:
- spawn: distance and height of every new member / item from the site on the first server tick after the job created it (limit 5 m / 3 m);
- first online tick: every member / item is looked at on the first tick it exists as an online object (the player is moved next to the site):
  height vs the site (limit 4 m) and height vs its own AI node (limit 1.5 m: online NPCs sit on their node, so this finds anything spawned below
  or inside geometry whatever the slope); the horizontal spread is logged;
- 30 s later: alive, no other stalker within 80 m (snapshot at 6 s), no anomaly zone within 15 m.

Measured with the live console (dedicated server + client, `tools\stalker_xrmpe\live`, 0.25 s sampling, player teleported next to the site after the
job was accepted far away):
| job | spawn tick | first online tick | what the old number was |
|---|---|---|---|
| rq_sid_camp (97 13 612), 4 members | 0.0 m | max dy 0.7 m (13.1 to 13.8), nearest node 0.0 | 8.2 m was the slope the bandits climbed: +5.7 m in 4.5 s (13.1 to 18.8 at z 623), 20 m in 10 s |
| rq_bar_kill1 (23 5 360), 3 runs | 0.0 m | max dy 0.89 / 0.85 / 0.72 m, max horizontal 1.2 / 0.8 / 0.8 m | 4.3 m was the mercenaries walking to the player |
| rq_hun_camp (3 239), 2 runs, 5 and 6 members | 0.0 m | max dy 0.23 / 0.43 m, max horizontal 1.9 / 4.5 m | 6.3 m was the pack roaming: animals of a squad walk 10 to 16 m from the site within 5 s even when the player is neutral |
| rq_bar_camp2 (same site) | 0.0 m | max dy 0.98 m, horizontal 1.5 m | |
No site had to change for the Cordon and Bar jobs; the rule is documented here instead of loosening a limit. After the first online tick the squads
walk: that is the normal behaviour of the simulation (targets hunt the player), not a spawn error.

Yantar batch (run folder `rqyana1`: Cordon start, party vote to Yantar, 3 jobs, 23 checks): 22 PASS, 1 FAIL.
- `rq_sak_camp1`, `rq_sak_camp2`: all checks PASS (spawn 0.0 m, first online dy 0.2 / 0.0 m, node dy 0.27 / 0.03 m, spot, nearest stalker 87 / 173 m,
  anomaly 178 / 287 m, alive 30 s).
- `rq_sak_find`: item at the site, spot, y, anomaly PASS; **FAIL "no other NPC within 80 m": a zombie stalker 36 m away**. Cause (patrol paths of
  `all.spawn`, checked offline): the Yantar zombie squads walk patrol routes far outside their smart terrain; the site (144 6 24) lies 13 m from points of
  `yan_smart_terrain_3_z_patrol_2/3` and `5_z_patrol_1`, although the nearest smart terrain is 85 m away. The audit above only used smart terrain
  centres. Patrol clearance of all 28 sites (nearest patrol point of the level, any kind): Cordon 20 to 86 m (`rq_wolf_camp2` 20 m is its own dog den),
  Bar 54 to 119 m (the 54 m ones are the boar den), Yantar camp2 83 m, camp1 25 m (the snork den walker, as designed) and find 13 m (zombies).
  Better site for the find job, measured the same way: **(-252.0, -18.9, -42.7), level vertex 71, game vertex 1690** (west corner: 180 m from every
  human / zombie patrol point, 193 m from the nearest smart terrain, 310 m from anomalies, 370 m from Sakharov; a snork den path is 55 m away).
  Test hook `batch_yan.lua` already uses it. It is NOT in `coop_repeat_quests.ltx` yet: the machine ran out of commit memory before the
  re-run could prove it (see below), and unproven sites do not go into the shipped data. To apply: replace the `site =` line of `[rq_sak_find]` with
  `site = -252.0, -18.9, -42.7, 71, 1690`, then run `batch_yan.lua`.

Not re-run as a whole after the rule change (the rule was measured with the live console above): the Cordon batch (6 jobs) and the Bar batch (19 jobs).
Their last full results are the ones listed at the top of this block. After the Yantar run the PC went out of commit memory without any game running
(committed 30.8 of 31.5 GB, kernel paged pool growing by about 5 MB/s while Windows Search indexed; the 9 GB headroom rule for launching a game was
never met again), so no further game could be started.

## Map spots (hint, sync, removal)
- Hint: each job has its own string `rq_spot_<job>` (eng + rus): job name, a line break and the NPC's short job description, for example
  "Clear the bandit camp / A bandit gang set up a camp ..." (rus: "Уничтожить лагерь бандитов" and the description), shown when the marker is hovered.
  The script translates it on the server (so the language of the host is used) and gives the engine the translated text.
- Add: `map_add_object_spot_ser` on the server and now also `map_sync_spot(id, type, SV_OBJECT_ID)` (the way the mod's `treasure_manager` sends its spots
  to every client; without it only the host had the markers). A client that joins later gets the spots of the running jobs in `catch_up()`.
- Remove: `remove_spot()` calls `map_remove_object_spot` unconditionally (the old `xr_effects.remove_spot_from_map` only removed a spot when
  `map_has_object_spot` was true, which is false once the target squad has been released) and repeats it while a duplicate is left. It runs for
  every end of a job: targets dead (killed by anyone, or removed), hand-in, cancel / fail flag, timeout. Spot objects are kept in the `RQ_<job>_P<id>` story flags
  (saved with the game), so a job that is still open after a load keeps its spot id and is cleaned up when it ends.
- Test `tests/rq_spot_hooks.lua` (dedicated server + one real remote client A, Cordon; a second client crashed at start-up, out of memory): for three jobs
  (targets removed by others, hand-in done flag, cancel / fail flag) the client must show the spot (`level.map_has_object_spot`) after the job was accepted and
  must not show it after the job ended. Result with the first version of this fix: the spot reaches the client in all three cases (sync works, the
  hint text handed to the engine was e.g. "Hunt down a bandit patrol / A bandit patrol is cutting the road to my bunker. ..."), it is gone on the client
  after the hand-in (item) and after cancel (squad still existing), but NOT after the targets were killed / released: the server drops its copy of
  the spot together with the squad and never tells the client (client `has_spot` stayed true). Fix: `sim_squad_scripted_cl_manager.dscript` wraps
  `sim_squad_cl_manager:remove_squad`, which every client runs when a squad is removed, and calls `coop_repeat_quests.on_squad_removed` to drop the local
  copy of the spot.
- Re-test of the fix (2026-10-21, live console, dedicated server + real client A, Cordon, stage = v1.3 lite + this patch; session logs
  `tools\stalker_xrmpe\live\logs\lvrqa261021_075111` and `lvrqb261021_082252`). Every end of a job, checked on the server and on the client
  (`level.map_has_object_spot`):
  | case | job | spot on the client after accept | spot on the client after the end |
  |---|---|---|---|
  | targets really killed (3 bandits, hits) | rq_sid_kill | yes (13313) | gone, job done, flags cleared |
  | targets removed by others (`sim_board:remove_squad`, 2 squads) | rq_wolf_camp1 | yes (13594) | gone; `on_squad_removed` ran on the client for both squads (13594, 13619) |
  | hand-in (done flag), item job | rq_shu_find | yes (14080, green) | gone |
  | cancel (fail flag), squads still alive | rq_sid_camp | yes (14081) | gone, squad still exists |
  | save / load | rq_sid_camp | the save was made with the job running; a new session booted from it: story flags, server spot and the late joining client A show the spot (14883) | 5 targets killed after the load: gone on the client, job done |
  Control: with the new client hook neutralised the spot was ALSO gone on the client in two tries (a squad removed, and a plain spot on a removed squad), so
  the server's own removal reaches the client in those runs; the hook stays as a second path for the case where the server already dropped its copy
  (the situation of the first failing test), which these runs did not reproduce. Not shown: the formal `rq_spot_hooks.lua` run of this build (no game
  could be started, see above). Harness note: `live.load_last()` on a running dedicated session left client A frozen while reconnecting (7 minutes, no
  answer); loading by booting from a save (`start_live -Save`) works.
- Game time: the clock of a dedicated server advanced by 64 game minutes within a few seconds around a save once, which made the 60 minute defend job
  time out right away; kill / camp jobs have a 2880 minute limit and were not affected.

## Multiplayer risks / confidence
- Reset waits until the players are on the quest's level; the game-time cooldown keeps running meanwhile.
- If .dscript appending is changed by a future xrMPE, ship client_tasks.script instead.

## Test (real game, Cordon, listen server, test bot, cooldown shortened to 2 game minutes in the test build only)
All PASS: dog-tail quest accepted (restrictor gives task, cycle 0) -> 10 dog tails handed in -> reward 2000 paid once, task closed ->
still locked before cooldown -> after forwarding game time the accept/done flags are cleared and cycle 1 starts -> accepted again, script re-gives the task
-> turned in again, 2000 paid exactly once more. Late-join catch-up fired for a forgotten actor id. Kill quest (mutant dogs): cycle 0 spawns the squad,
squad death completes it, after the cooldown it is offered again, cycle 1 gives the task and re-creates the squad.
Not tested: two real players (late join was simulated by forgetting the actor id), Bar/Yantar quests (same data pattern, generated from the same files).

## Test: text (real game, Cordon, listen server, test bot `tests/rq_loc_hooks.lua`)
Russian run (registry `InstallLang` = rus for the client start, restored to eng after): all 201 ids return exactly the Russian strings of the rus
file (cp1251, no id left, no Latin letters in the six lines FOSTER reported), the Sidorovich talk window opens and its screenshot lists
"Есть для меня работа?" as option 1 with the Sidorovich name and the rest of the window in Russian. English run: all 201 ids return exactly the
English strings, same window shows "Do you have any work for me?". Offline: every id used by the dialogs, `tm_coop_repeat.ltx` and the map spots exists in
both files. Not clicked by the bot: the second dialog level (reply and the job options); those lines are covered by the id check.


## v1.4: fetch jobs, the mod's own task menu removed, icons, hand-in visibility, task audit

### The mod's generic task menu ("I need work, what have you got?") is gone
It is not ours and not SoC: it is the level maker's `*_secondary_quests_dialog` (dialog_0 "I need work, what have you got?" with the sub menu "Find an artifact /
Kill a stalker / Clear the area of mutants / Find a mutant part / Nothing", flags `*_SQ_*_STOP_DIALOG_INFO`, tasks `*_start_sq_*_quest_task`, 30 tasks, one-shot
restrictors). Removed the least invasive way: the `<actor_dialog>` line of the dialog is commented out in the three `character_desc_*.xml` files of this patch
(no shared dialog xml was touched, so nothing else has to change). NPCs that had it: Sidorovich (Cordon), the Barman (Bar), Sakharov and Kruglov (Yantar);
the Bar hunter's copy was already commented out in the mod. Nothing else refers to it: the PDA phrases (`coop_pda_phrases`) and `story_flags_table` only
define names, nothing counts the tasks. A task of that system that is already running in a save stays completable: the giver's `*_secondary_quests_idle_dialog`
(hand-in) and `*_fail_dialog` (cancel) are kept, they only show while such a task runs (`quest_dialogs`). The 26 `esc/bar/yan_start_sq_*` entries of
`coop_repeat_quests.ltx` (their refresh) were removed too. So the "18 art / part jobs that spawn nothing" were THIS menu's jobs: they were offered, but by
the level maker's menu, never by our dialogs (ours offered camp / kill / defend only).

### Fetch jobs (kind = gen_fetch): bring an artifact / a mutant part
Since v1.4.1 the patch has the WHOLE SoC set of artifact and mutant part orders: every `tm_find_artefact_*`, `tm_monster_part_*`, `barmen_find_artefact_*`, `barmen_monster_part_*`, `ecolog_find_artefact_*`,
`ecolog_monster_part_*` and `freedom_monster_part_1` of the Steam SoC `misc\task_manager.ltx` (23 jobs: Sidorovich 5, Barman 7, Sakharov 10, Lukash 1), each with the SoC giver, item, pay and priority. (The first v1.4.1 build had 12 jobs, 4 per giver,
two of them not SoC orders: the Cordon dog tail / boar hoof orders are gone, Sidorovich now asks for the SoC bloodsucker jaw and pseudodog tail.) No other SoC giver has artifact or part orders (Duty, Wolf, Hunter etc. only kill, camp, defend, find-item).
`tools/gen_fetch.py` holds the table and writes every fetch part of the patch (ltx, task sections, dialogs, strings, the FETCH table and functions of `coop_rq_dialogs.script`); run it again after any change (idempotent).
`tools/soc_fetch_texts.py` collected the original SoC texts into `tools/fetch_texts.json` (English: Steam SoC `stable_task_manager.xml`; Russian: `st_soc_strings.xml` of the original Russian SoC).

| job | giver | SoC order | task / menu text (SoC English) | item (mod sections, SoC twin accepted) | pay to the player who hands in | offered |
|---|---|---|---|---|---|---|
| rq_sid_art1 | Sidorovich (Cordon) | tm_find_artefact_1 (priority 1) | Find the Jellyfish artifact | af_medusa, af_medusa_soc | 1500 RU and a bottle of vodka | from the start |
| rq_sid_art2 | Sidorovich (Cordon) | tm_find_artefact_2 (priority 2) | Find the Stone Flower artifact | af_cristall_flower, af_cristall_flower_soc | 3000 RU and a bottle of vodka | from the start |
| rq_sid_art4 | Sidorovich (Cordon) | tm_find_artefact_4 (priority 3) | Find the artifact called Chunk of Meat | af_mincer_meat, af_mincer_meat_soc | 2500 RU and 3 army medkits | from the start |
| rq_sid_part1 | Sidorovich (Cordon) | tm_monster_part_1 (priority 2) | Bring the jaw of the bloodsucker | mutant_krovosos_part | 3000 RU and 5 boxes of 12x76 Dart shells | after the military case was taken (SoC info agroprom_military_case_have, flag AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO) |
| rq_sid_part2 | Sidorovich (Cordon) | tm_monster_part_2 (priority 1) | Bring over the tail of the pseudodog | mutant_psevdodog_part | 1500 RU and 5 boxes of 12x76 Dart shells | from the start |
| rq_bar_art1 | Barman (Bar) | barmen_find_artefact_1 (priority 1) | Find the Meat chunk artifact | af_mincer_meat, af_mincer_meat_soc | 2500 RU and 2 science medkits | from the start |
| rq_bar_art2 | Barman (Bar) | barmen_find_artefact_2 (priority 3) | Find the Crystal Thorn artifact | af_rusty_kristall_soc | 2500 RU, 2 science medkits and 2 Antirads | after the X18 documents were handed to the Barman (SoC bar_darklab_document_done, flag BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO) |
| rq_bar_art3 | Barman (Bar) | barmen_find_artefact_3 (priority 4) | Find the Night Star artifact | af_night_star, af_night_star_soc | a Berill-5M armored suit and 3 F-1 grenades | from the start |
| rq_bar_art4 | Barman (Bar) | barmen_find_artefact_4 (priority 2) | Find the artifact Flash | af_electra_flash, af_electra_flash_soc | 5000 RU | after the X18 documents were handed to the Barman (SoC bar_darklab_document_done, flag BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO) |
| rq_bar_art5 | Barman (Bar) | barmen_find_artefact_5 (priority 5) | Find artifact Goldfish | af_gold_fish, af_gold_fish_soc | an LR-300, an M203 grenade launcher, a SUSAT scope and a silencer | after leaving laboratory X16 (SoC yan_kill_brain_done, stood for by flag X16_START_GET_OUT_OF_THE_LAB_TASK_INFO) |
| rq_bar_part1 | Barman (Bar) | barmen_monster_part_1 (priority 1) | Obtain the flesh's eye | mutant_flesh_part | 500 RU and 3 cans of food | from the start |
| rq_bar_part2 | Barman (Bar) | barmen_monster_part_2 (priority 2) | Bring the hoof of a boar | mutant_boar_part | 1500 RU | from the start |
| rq_sak_art1 | Sakharov (Yantar) | ecolog_find_artefact_1 (priority 3) | Bring the Fireball artifact | af_fireball, af_fireball_soc | a "Pellicle" artifact | from the start |
| rq_sak_art2 | Sakharov (Yantar) | ecolog_find_artefact_2 (priority 1) | Find the "Gravi" artifact | af_gravi, af_gravi_soc | 5000 RU and a science medkit | from the start |
| rq_sak_art3 | Sakharov (Yantar) | ecolog_find_artefact_3 (priority 2) | Find the "Jellyfish" artifact | af_medusa, af_medusa_soc | 2500 RU and a science medkit | from the start |
| rq_sak_art4 | Sakharov (Yantar) | ecolog_find_artefact_4 (priority 4) | Find the "Moonlight" artifact | af_electra_moonlight, af_electra_moonlight_soc | 10000 RU and 3 science medkits | from the start |
| rq_sak_art5 | Sakharov (Yantar) | ecolog_find_artefact_5 (priority 5) | Find the artifact called Sea Urchin | af_rusty_sea-urchin_soc | a SEVA bodysuit | from the start |
| rq_sak_part1 | Sakharov (Yantar) | ecolog_monster_part_1 (priority 1) | Bring a part of the snork's body | mutant_snork_part | 2500 RU and a science medkit | from the start |
| rq_sak_part2 | Sakharov (Yantar) | ecolog_monster_part_2 (priority 2) | Bring the eye of a flesh | mutant_flesh_part | 1000 RU and a SUSAT scope | from the start |
| rq_sak_part3 | Sakharov (Yantar) | ecolog_monster_part_3 (priority 3) | Bring the tail of a blind dog | mutant_boar_part | 2000 RU and 3 boxes of 12x76 Dart shells | from the start |
| rq_sak_part4 | Sakharov (Yantar) | ecolog_monster_part_4 (priority 4) | Bring the leg of a boar | mutant_psevdodog_part | 3000 RU and a science medkit | from the start |
| rq_sak_part5 | Sakharov (Yantar) | ecolog_monster_part_5 (priority 5) | Bring the bloodsucker's jaw | mutant_krovosos_part | 6000 RU and a science medkit | from the start |
| rq_fre_part1 | Lukash, Freedom leader (Army Warehouses) | freedom_monster_part_1 (priority 1) | Bring a boar's leg | mutant_boar_part | 1000 RU and a bottle of vodka | from the start |

Not offered: `tm_find_artefact_3` (Night Star for Sidorovich). In SoC it needs the info `esc_darklab_documents_read`, which only a Sidorovich dialog for the X18 documents sets; this mod has no such dialog,
and its only reward `outfit_stalker_m2` exists neither in SoC nor in the mod. Where a SoC reward is an item the mod does not have under that name, the mod's twin is used (`af_dummy_pellicle` -> `af_dummy_pellicle_soc`).
Not paid (the old fetch jobs did not either): SoC reputation / rank / community goodwill of an order.

**Menu (the same "Do you have any work for me?" menu as the kill / camp / defend jobs).** Offer, giver line, accept phrase of every job are phrases of the giver's own job dialog (`rq_sid_dialog`, `rq_bar_dialog`,
`rq_sak_dialog`, new `rq_fre_dialog` on Lukash). SoC did not list every order: its task manager (`CRandomTask:task_avail`) offers per giver and per type only the AVAILABLE order with the lowest `prior`, and only one order of a type
can run at a time (`active_task_by_type`); an order waits `idle_time` (24 h) after it was done. The mod does the same with a Lua precondition on each offer phrase (`coop_rq_dialogs.offer_<job>`, one of the story flags
above is the SoC `condlist`): an order is offered when its gate flags are set, it is not accepted (accept flag; after done / fail the repeat script clears the flags when the cooldown is over), no other order of the same
giver and kind is running, and no available order of that giver and kind has a lower priority. So the menu never grows: at most one artifact and one part order per giver at a time, that is Sidorovich 3 fixed + 2 = 5 entries,
Barman 5 + 2 = 7, Sakharov 3 + 2 = 5, Lukash 1 (plus "Not now"). Example: Sidorovich offers Jellyfish and the pseudodog tail; after the Jellyfish is handed in the next artifact (Stone Flower) appears, the Jellyfish comes back
after 24 game hours; the bloodsucker jaw (priority 2) shows up after the pseudodog tail is done AND the military case was taken. `tools/check_rq.py` prints the longest possible menu of every giver and fails above 9 entries.

- Flow: the accept phrase sets `RQG_<ID>_ACC`; `coop_repeat_quests.script` (kind `gen_fetch`) gives the PDA task to every player, spawns nothing, adds no map spot (fetch jobs have no location) and sets only the start time;
  cooldown 1440 game minutes after done / fail and the 2880 minute timeout are the defaults, so the host settings `cooldown_min` / `timeout_mult` apply as for the other jobs. A client's story flag
  `RQ_NO_ITEM_REWARDS` (set by the server from the host setting `item_rewards = false`) drops the reward items, the money stays. A job that pays only items (Night Star, Gold Fish, Sea Urchin, Pellicle) pays nothing then.
- Hand-in: the giver's hand-in dialog (`rq_sid_handin`, `rq_bar_handin`, `rq_sak_fetch_handin`, `rq_fre_handin`; first line SoC `tm_reward_job`, the giver asks SoC `tm_<giver>_job_ask`, the player picks the job by its SoC title, the giver answers SoC `tm_<giver>_job_complete`).
  The talking player's inventory is searched (artifact and its SoC twin), ONE piece is taken from THAT player (`dialogs.relocate_item_section_from_actor`) and money / items are paid to THAT player (`relocate_money_to_actor` /
  `relocate_item_section_to_actor`, no "+0 RU" for item-only pay); the phrase sets `RQG_<ID>_DONE`, which completes the task for everybody (the task section has no reward_money, so nobody else is paid).
- Text: SoC original wording in English and Russian (title = menu line and PDA name, giver line, PDA description, "I'm up for it." / "Я берусь."), PDA description ends with the hand-in giver and the pay. eng + rus have identical id sets (367 ids per language).

### Hand-in visibility (all givers) and Nimble
The hand-in option ("I found what you asked for.") showed without any job. Now every hand-in dialog has a dialog-level precondition: it shows only while THE TALKING PLAYER has a
running job of that giver (accepted, not done, not failed) AND carries the item (`coop_rq_dialogs.fetch_open_<giver>`, `find_open_<giver>`; flags are synced story flags, the
inventory is the local player's). Covers Wolf, Voronin, the Informant, Zhorik, Sakharov (find jobs) and Sidorovich, the Barman, Sakharov, Lukash (fetch jobs).
Nimble (Shustry) is no longer a repeatable-quest giver: `rq_shu_dialog` / `rq_shu_handin` are gone from his character; his "Find a lost pistol" job (`rq_shu_find`, id unchanged)
now belongs to Wolf (`rq_wolf_dialog`, `rq_wolf_handin`); Sidorovich has the fetch jobs, so it was not added to him.

### Task icons
The question mark came from the level maker's icons (`ui_ingame2_esc_start_sq_*`: region x = 747 of `ui_actor_newsmanager_icons`, a white "?" silhouette / dark cells). Now every job uses SoC's own
icons copied from the SoC `ui_iconsTotal` atlas (FOSTER's `ui_iconstotal.dds`, identical to the Steam one) into `textures/ui/ui_rq_task_icons.dds` + `configs/ui/textures_descr/ui_rq_task_icons.xml`
(7 cells of 83 x 47, A8R8G8B8, tool `tools/make_icons.py`): the giver's face for Sidorovich (`ui_iconsTotal_esc_trader_job`), the Barman (`bar_barman_job`), Sakharov and Kruglov (`yan_scientist_job`);
other givers get SoC's task-type icon (`kill_stalker`, `eliminate_lager`, `defend_lager`, `find_item`). New ids: `ui_rq_job_trader|barman|scientist`, `ui_rq_task_kill|camp|defend|find`. `tools/check_rq.py` checks that every icon id exists.

### Task audit (the level maker's tasks vs original SoC)
Hidden for good (never given: `client_tasks.give_task_to_client` ignores the ids of `configs/misc/coop_hidden_tasks.ltx`, so restrictors, dialogs and other tasks that call `give_task` do nothing for them):
Beginning of beginnings (`esc_start_main`), Rest on duty, Rescue Fox, Save Yurik, Talk to Yurik, the 3 "Measurements started" and 3 "Measurements interrupted" steps. Rule: not in SoC AND no `give_task` chain, no info set at
completion that anything reads, nothing refers to the id. Tasks that were already given in a save stay in the PDA until they end by themselves (their flags still drive them).
Everything else in the table is kept: the SoC ones (kept as they are), and the other level-maker tasks that link into the story chain (`give_task` of the next task from the completion): hiding those needs a silent
task runner (the completion actions must still run), which cannot be proven offline, so they are only listed. "renamed" = the same story beat as the SoC task named, with the mod's own title. The mapping is by title and story beat; FOSTER should confirm the "no clear match" and "travel hint" rows.
Reward money of the hidden tasks is lost with them (none is a story reward).
| task | title (rus) | level | in SoC? | what it sets / gives | action |
|---|---|---|---|---|---|
| esc_start_main | Начало начал | _escape | no (SoC starts with tutorial_find_artefact) | complete flag only | hidden: never given |
| esc_start_talk_to_the_sidorovich | Важное поручение | _escape | renamed (esc_flash_task (Important mission, flash drive)) | gives esc_start_find_stalker | kept: gives esc_start_find_stalker_shustry, esc_start_talk_to_the_wolf |
| esc_start_find_stalker_shustry | Важное поручение | _escape | renamed (esc_flash_task (Important mission, flash drive)) | complete flag only | kept (leaf, no dependency) |
| esc_start_talk_to_the_wolf | Разузнать про ситуацию с Шустрым | _escape | renamed (tutorial_help_wounded / esc_flash_task) | gives esc_start_save_the_sta | kept: gives esc_start_save_the_stalker_shustry, esc_start_talk_to_petruha |
| esc_start_save_the_stalker_shustry | Спасти сталкера Шустрого | _escape | renamed (tutorial_help_wounded / esc_flash_task) | gives esc_start_escort_the_s | kept: gives esc_start_escort_the_stalker_shustry |
| esc_start_escort_the_stalker_shustry | Спасти сталкера Шустрого | _escape | renamed (tutorial_help_wounded / esc_flash_task) | complete flag only | kept (leaf, no dependency) |
| esc_start_talk_to_petruha | Своих не бросаем | _escape | renamed (esc_dinamit_to_volk) | gives esc_start_kill_bandits | kept: gives esc_start_kill_bandits_on_the_atp |
| esc_start_kill_bandits_on_the_atp | Рейд на АТП | _escape | renamed (esc_dinamit_to_volk) | gives esc_start_go_back_to_t | kept: gives esc_start_go_back_to_the_wolf |
| esc_start_go_back_to_the_wolf | Вернуться к Волку | _escape | renamed (esc_dinamit_to_volk) | complete flag only | kept (leaf, no dependency) |
| esc_start_talk_to_the_sidorovich_quest_1 | Похоже, что-то намечается | _escape | renamed (esc_help_wounded_from_raid) | gives esc_start_talk_to_the_ | hidden: never given (patch cordon replaced the helicopter flight and this task by the original SoC chain: Sidorovich's military case talk right after the flash drive) |
| esc_start_talk_to_the_fox_quest_1 | Лис может что-то знать | _escape | renamed (esc_help_wounded_from_raid) | gives esc_start_talk_to_the_ | hidden: never given (the Fox detour is gone, patch cordon) |
| esc_start_talk_to_the_fox_quest_2 | Дорога на север | _escape | renamed (esc_help_wounded_from_raid) | complete flag only | hidden: never given (replaced by the SoC tasks "Get to the railroad embankment" and "Find the militaries' documents", patch cordon) |
| esc_start_kill_dogs | Спасение Лиса | _escape | no | complete flag only | hidden: never given |
| esc_start_5_bottles_of_vodka_for_kuznetsov | Отдохнуть на службе | _escape | no | complete flag only | hidden: never given; the bridge pass costs 500 rubles as in SoC (patch cordon), the task text says so |
| esc_start_sq_art_1 | Заказ на "Медуза" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_art_2 | Заказ на "Кровь камня" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_art_3 | Заказ на "Каменный цветок" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_killer_1 | Заказ на сталкера "Макрушник" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_killer_2 | Заказ на сталкеров "3 балбеса" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_killer_3 | Заказ на сталкера "Снайпера-неудачника" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_killer_mutants_1 | Заказ на мутантов "Овраг около Деревни новичков" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_killer_mutants_2 | Заказ на мутантов "Холм за АТП" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_killer_mutants_3 | Заказ на мутантов "Овраг около Элеватора" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_mutant_boar_part_1 | Заказ на "Копыто Кабана" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_mutant_dog_part_2 | Заказ на "Хвост Собаки" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| esc_start_sq_mutant_flesh_part_3 | Заказ на "Глаз Плоти" | _escape | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| gar_start_save_the_stalker_yurik_from_bandits | Спасти Юрика | _garbage | no | complete flag only | hidden: never given |
| gar_start_talk_to_yurik | Поговорить с Юриком | _garbage | no | complete flag only | hidden: never given |
| gar_start_talk_to_devil | Преступление и наказание | _garbage | renamed (gar_help_dymon) | gives gar_start_help_to_repe | kept: gives gar_start_help_to_repel_the_bandits_attack |
| gar_start_help_to_repel_the_bandits_attack | Преступление и наказание | _garbage | renamed (gar_help_dymon) | gives gar_start_talk_to_devi | kept: gives gar_start_talk_to_devil_1 |
| gar_start_talk_to_devil_1 | Преступление и наказание | _garbage | renamed (gar_help_dymon) | complete flag only | kept (leaf, no dependency) |
| gar_start_help_the_gray_to_fight_off_the_bandits | Полный беспредел | _garbage | renamed (garbage_meet_stalker / gar_car_graveyard_quest) | gives gar_start_talk_to_gray | kept: gives gar_start_talk_to_gray |
| gar_start_talk_to_gray | Полный беспредел | _garbage | renamed (garbage_meet_stalker / gar_car_graveyard_quest) | gives gar_start_go_to_the_ag | kept: gives gar_start_go_to_the_agroprom |
| gar_start_go_to_the_agroprom | На Агропром | _garbage | no (travel hint) | complete flag only | kept (leaf, no dependency; travel hint / unclear: FOSTER decides) |
| gar_start_help_fight_off_the_mutants | Волна мутантов | _garbage | renamed (gar_kill_boars) | complete flag only | kept (leaf, no dependency) |
| agr_start_save_the_stalker_mole | Загнанный в угол | _agroprom | renamed (agr_help_krot) | gives agr_start_follow_the_s | kept: gives agr_start_follow_the_stalker_mole |
| agr_start_follow_the_stalker_mole | Загнанный в угол | _agroprom | renamed (agr_help_krot) | gives agr_start_talk_to_the_ | kept: gives agr_start_talk_to_the_stalker_mole |
| agr_start_talk_to_the_stalker_mole | Загнанный в угол | _agroprom | renamed (agr_help_krot) | gives agr_start_go_to_the_ag | kept: gives agr_start_go_to_the_agroprom_underground |
| agr_start_go_to_the_agroprom_underground | Пора в подъземелье | _agroprom | renamed (agroprom_get_military_documents) | complete flag only | kept (leaf, no dependency) |
| agr_start_break_into_a_military_base | Вломиться на базу военных | _agroprom | renamed (agroprom_get_military_documents) | sets AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO | kept: gives agr_start_the_destination_is_a_bar |
| agr_start_the_destination_is_a_bar | Пункт назначения - Бар | _agroprom | no (travel hint) | complete flag only | kept (leaf, no dependency; travel hint / unclear: FOSTER decides) |
| agru_start_find_the_shooter_hiding_place | Отыскать тайник Стрелка | _agroprom_underground | yes (agroprom_find_gunslinger_cache) | sets AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO | kept: gives agru_start_return_to_the_surface |
| agru_start_return_to_the_surface | Возвращение на поверхность | _agroprom_underground | no (travel hint) | complete flag only | kept (leaf, no dependency; travel hint / unclear: FOSTER decides) |
| val_start_sneak_into_the_x_18_lab_1 | Пробраться в лабораторию X-18 | _darkvalley | renamed (bar_darklab_documents / bar_darklab_documents2) | gives x18_start_go_to_x18_do | kept: gives x18_start_go_to_x18_doc_1, x18_start_go_to_x18_doc_2... |
| val_start_take_the_documents_to_the_barmen | Возвращение к Бармену | _darkvalley | renamed (bar_darklab_documents / bar_darklab_documents2) | gives bar_start_go_to_yantar | kept: gives bar_start_go_to_yantar |
| val_start_go_to_the_sos_signal_1 | Сигнал SOS | _darkvalley | renamed (val_captive_help / val_prisoner_help) | gives val_start_go_to_the_so | kept: gives val_start_go_to_the_sos_signal_2 |
| val_start_go_to_the_sos_signal_2 | Сигнал SOS | _darkvalley | renamed (val_captive_help / val_prisoner_help) | complete flag only | kept (leaf, no dependency) |
| val_start_fake_gauss_1 | Новое оружие | _darkvalley | renamed (val_captive_help / val_prisoner_help) | gives val_start_fake_gauss_2 | kept: gives val_start_fake_gauss_2 |
| val_start_fake_gauss_2 | Новое оружие | _darkvalley | renamed (val_captive_help / val_prisoner_help) | complete flag only | kept (leaf, no dependency) |
| val_start_follow_the_bullet | Пленник поневоле | _darkvalley | renamed (val_captive_help / val_prisoner_help) | gives val_start_save_the_pri | kept: gives val_start_save_the_prisoner |
| val_start_save_the_prisoner | Пленник поневоле | _darkvalley | renamed (val_captive_help / val_prisoner_help) | complete flag only | kept (leaf, no dependency) |
| x18_start_go_to_x18_doc_1 | В поисках тайн | _x18 | renamed (bar_darklab_documents2) | sets X18_START_GO_TO_X18_DOC_1_TASK_INFO | kept (leaf, no dependency) |
| x18_start_go_to_x18_doc_2 | В поисках тайн | _x18 | renamed (bar_darklab_documents2) | sets X18_START_GO_TO_X18_DOC_2_TASK_INFO | kept (leaf, no dependency) |
| x18_start_go_to_x18_doc_3 | В поисках тайн | _x18 | renamed (bar_darklab_documents2) | sets X18_START_GO_TO_X18_DOC_3_TASK_INFO | kept (leaf, no dependency) |
| x18_start_get_out_of_the_lab | На выход! | _x18 | no (X-18 step) | complete flag only | kept (leaf, no dependency; travel hint / unclear: FOSTER decides) |
| x18_start_find_the_password_x18_codedoor_1 | "Заперто!" | _x18 | yes (dar_codedoor_1 / dar_codedoor_2) | complete flag only | kept (leaf, no dependency) |
| x18_start_find_the_password_x18_codedoor_2 | "Снова заперто!" | _x18 | yes (dar_codedoor_1 / dar_codedoor_2) | complete flag only | kept (leaf, no dependency) |
| x18_start_kill_the_flame_poltergeist | "Не опять, а снова заперто!" | _x18 | no (X-18 step) | gives x18_start_get_out_of_t | kept: gives x18_start_get_out_of_the_lab |
| bar_start_sneak_into_the_x_18_lab | Пробраться в лабораторию X-18 | _bar | renamed (bar_darklab_documents / bar_darklab_documents2) | sets BAR_START_SNEAK_INTO_THE_X_18_LAB_QUEST_TASK_INFO | kept: gives val_start_sneak_into_the_x_18_lab_1 |
| bar_start_go_to_yantar | Светила науки | _bar | renamed (bar_resque_information / _2) | complete flag only | kept (leaf, no dependency) |
| bar_start_go_to_military | Пора в центр Зоны! | _bar | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives mil_start_go_to_radar_ | kept: gives mil_start_go_to_radar |
| bar_start_find_the_family_gun | Найти фамильное ружьё | _bar | yes (bar_hunter_rifle) | complete flag only | kept (leaf, no dependency) |
| bar_start_the_meeting_place_cannot_be_changed_1 | Место встречи изменить нельзя | _bar | no clear match | gives bar_start_the_meeting_ | kept: gives bar_start_the_meeting_place_cannot_be_changed_3 |
| bar_start_the_meeting_place_cannot_be_changed_2 | Место встречи изменить нельзя | _bar | no clear match | gives bar_start_the_meeting_ | kept: gives bar_start_the_meeting_place_cannot_be_changed_3 |
| bar_start_the_meeting_place_cannot_be_changed_3 | Место встречи изменить нельзя | _bar | no clear match | complete flag only | kept (leaf, no dependency; travel hint / unclear: FOSTER decides) |
| bar_start_sq_art_1 | Заказ на "Выверт" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_art_2 | Заказ на "Грави" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_art_3 | Заказ на "Золотая рыбка" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_mutant_psevdodog_part_1 | Заказ на "Хвост Псевдособаки" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_mutant_snork_part_2 | Заказ на "Стопа Снорка" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_mutant_krovosos_part_3 | Заказ на "Щупальца Кровососа" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_killer_mutants_1 | Заказ на мутантов "NoN" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_killer_mutants_2 | Заказ на мутантов "NoN" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| bar_start_sq_killer_mutants_3 | Заказ на мутантов "NoN" | _bar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| ros_start_go_to_yantar | Светила науки | _rostok | renamed (bar_resque_information / _2) | complete flag only | kept (leaf, no dependency) |
| ros_start_help_kruglov | Ради науки | _rostok | renamed (bar_resque_information / _2) | gives ros_start_escort_krugl | kept: gives ros_start_escort_kruglov_to_yantar |
| ros_start_escort_kruglov_to_yantar | Ради науки | _rostok | renamed (bar_resque_information / _2) | complete flag only | kept (leaf, no dependency) |
| mil_start_talk_to_the_cap | Защита Барьера | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_protect_the_ | kept: gives mil_start_protect_the_barrier |
| mil_start_protect_the_barrier | Защита Барьера | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_go_to_radar | Пора в центр Зоны! | _military | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives rad_start_go_to_radar_ | kept: gives rad_start_go_to_radar |
| mil_start_kill_the_sniper_on_the_tower | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_talk_to_skul | kept: gives mil_start_talk_to_skull_about_the_assault |
| mil_start_talk_to_skull_about_the_assault | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_kill_lukash_ | kept: gives mil_start_kill_lukash, mil_start_kill_the_snipers_1 |
| mil_start_kill_lukash | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_snipers_1 | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_kill_the_sni | kept: gives mil_start_kill_the_snipers_2 |
| mil_start_kill_the_snipers_2 | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_kill_the_sni | kept: gives mil_start_kill_the_snipers_3 |
| mil_start_kill_the_snipers_3 | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_kill_the_sni | kept: gives mil_start_kill_the_snipers_4 |
| mil_start_kill_the_snipers_4 | За Долг! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_report_to_max | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | gives mil_start_kill_skull_q | kept: gives mil_start_kill_skull, mil_start_kill_the_duty_1... |
| mil_start_kill_skull | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_1 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_2 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_3 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_4 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_5 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_6 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_7 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| mil_start_kill_the_duty_8 | За Свободу! | _military | renamed (mil_kill_sniper / mil_kill_lukash / mil_lukash_job / mil_blockpost_job) | complete flag only | kept (leaf, no dependency) |
| x16_start_find_the_installation | Найти установку в лаборатории X-16 | _x16 | renamed (bar_x16_documents) | gives x16_start_turn_off_the | kept: gives x16_start_turn_off_the_switch_1, x16_start_turn_off_the_switch_2... |
| x16_start_turn_off_the_switch_1 | Выключить рубильник №1 | _x16 | renamed (bar_x16_documents) | complete flag only | kept (leaf, no dependency) |
| x16_start_turn_off_the_switch_2 | Выключить рубильник №2 | _x16 | renamed (bar_x16_documents) | complete flag only | kept (leaf, no dependency) |
| x16_start_turn_off_the_switch_3 | Выключить рубильник №3 | _x16 | renamed (bar_x16_documents) | gives x16_start_turn_off_the | kept: gives x16_start_turn_off_the_switch_4 |
| x16_start_turn_off_the_switch_4 | Выключить рубильник №4 | _x16 | renamed (bar_x16_documents) | gives x16_start_get_out_of_t | kept: gives x16_start_get_out_of_the_lab |
| x16_start_get_out_of_the_lab | "Скорей на выход!" | _x16 | renamed (bar_x16_documents) | gives yan_start_talk_to_the_ | kept: gives yan_start_talk_to_the_barmen, yan_start_talk_to_the_saharov_x16_lab |
| yan_start_go_to_yantar | Светила науки | _yantar | renamed (bar_resque_information / _2) | gives yan_start_talk_to_the_ | kept: gives yan_start_talk_to_the_kruglov |
| yan_start_talk_to_the_kruglov | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | gives yan_start_take_measure | kept: gives yan_start_take_measurements_1 |
| yan_start_take_measurements_1 | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | gives yan_start_take_measure | kept: gives yan_start_take_measurements_2 |
| yan_start_take_measurements_2 | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | gives yan_start_take_measure | kept: gives yan_start_take_measurements_3 |
| yan_start_take_measurements_3 | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | gives yan_start_talk_to_the_ | kept: gives yan_start_talk_to_the_saharov |
| yan_start_talk_to_the_saharov | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | complete flag only | kept (leaf, no dependency) |
| yan_start_configuring_helmets | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | gives yan_start_infiltrate_t | kept: gives yan_start_infiltrate_the_x16_lab |
| yan_start_infiltrate_the_x16_lab | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | complete flag only | kept (leaf, no dependency) |
| yan_start_talk_to_the_saharov_x16_lab | Во имя науки! | _yantar | renamed (yan_find_scientist / yan_scientist_return_task / yan_find_vasilyev_task) | complete flag only | kept (leaf, no dependency) |
| yan_start_talk_to_the_barmen | Пора в центр Зоны! | _yantar | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives bar_start_go_to_milita | kept: gives bar_start_go_to_military |
| yan_start_wait_for_the_measurements_to_finish_1 | "Замеры начались!" | _yantar | no | complete flag only | hidden: never given |
| yan_start_return_to_the_measurement_location_1 | "Замеры прерваны!" | _yantar | no | complete flag only | hidden: never given |
| yan_start_wait_for_the_measurements_to_finish_2 | "Замеры начались!" | _yantar | no | complete flag only | hidden: never given |
| yan_start_return_to_the_measurement_location_2 | "Замеры прерваны!" | _yantar | no | complete flag only | hidden: never given |
| yan_start_wait_for_the_measurements_to_finish_3 | "Замеры начались!" | _yantar | no | complete flag only | hidden: never given |
| yan_start_return_to_the_measurement_location_3 | "Замеры прерваны!" | _yantar | no | complete flag only | hidden: never given |
| yan_start_sq_art_1 | Заказ на "Кристалл" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_art_2 | Заказ на "Огненный шар" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_art_3 | Заказ на "Глаз" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_mutant_snork_part_1 | Заказ на "Стопа Снорка" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_mutant_krovosos_part_2 | Заказ на "Щупальца Кровососа" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_mutant_chimera_part_3 | Заказ на "Коготь Химеры" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_killer_mutants_1 | Заказ на мутантов "На болоте около Бункера ученых" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_killer_mutants_2 | Заказ на мутантов "Справа от Бункера ученых" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| yan_start_sq_killer_mutants_3 | Заказ на мутантов "Около Упавшего вертолёта" | _yantar | no (generic task menu) | complete flag only | menu removed, not offered any more (a running one can still be finished) |
| rad_start_go_to_radar | Пора в центр Зоны! | _radar | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives x10_start_turn_off_the | kept: gives x10_start_turn_off_the_radar |
| x10_start_turn_off_the_radar | Пора в центр Зоны! | _x10 | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives x10_start_leave_the_bu | kept: gives x10_start_leave_the_bunker_and_go_to_pripyat |
| x10_start_leave_the_bunker_and_go_to_pripyat | Пора в центр Зоны! | _x10 | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | complete flag only | kept (leaf, no dependency) |
| pri_start_go_to_cnpp | Пора в центр Зоны! | _pripyat | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives aes_1_start_go_to_sarc | kept: gives aes_1_start_go_to_sarcofag |
| pri_start_meet_a_group_of_stalkers | Нет времени объяснять! | _pripyat | renamed (pripyat_task_1) | complete flag only | kept (leaf, no dependency) |
| pri_start_help_the_stalkers_get_to_the_underground_parking | Нет времени объяснять! | _pripyat | renamed (pripyat_task_1) | complete flag only | kept (leaf, no dependency) |
| con_start_sneak_into_the_control_room | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_destroy_the_ | kept: gives con_start_destroy_the_monolith_installation_1 |
| con_start_destroy_the_monolith_installation_1 | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_destroy_the_ | kept: gives con_start_destroy_the_monolith_installation_6 |
| con_start_destroy_the_monolith_installation_2 | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_destroy_the_ | kept: gives con_start_destroy_the_monolith_installation_5 |
| con_start_destroy_the_monolith_installation_3 | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_destroy_the_ | kept: gives con_start_destroy_the_monolith_installation_4 |
| con_start_destroy_the_monolith_installation_4 | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_talk_to_the_ | kept: gives con_start_talk_to_the_representative_awareness |
| con_start_destroy_the_monolith_installation_5 | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_destroy_the_ | kept: gives con_start_destroy_the_monolith_installation_3 |
| con_start_destroy_the_monolith_installation_6 | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_destroy_the_ | kept: gives con_start_destroy_the_monolith_installation_2 |
| con_start_talk_to_the_representative_awareness | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_kill_all_rep | kept: gives con_start_kill_all_representatives_of_awareness |
| con_start_kill_all_representatives_of_awareness | Пора со всем покончить! | _control_monolith | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | complete flag only | kept (leaf, no dependency) |
| sar_start_get_to_the_monolith | Тайна Зоны | _sarcofag | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives sar_start_kill_the_mon | kept: gives sar_start_kill_the_monolith_preacher |
| sar_start_kill_the_monolith_preacher | Пора со всем покончить! | _sarcofag | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives sar_start_search_the_p | kept: gives sar_start_search_the_preacher_body_and_retrieve_the_decoder |
| sar_start_search_the_preacher_body_and_retrieve_the_decoder | Пора со всем покончить! | _sarcofag | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | sets SAR_START_OPEN_THE_DOOR_TO_MONOLITH_MANAGEMENT_QUEST_TASK_INFO | kept: gives sar_start_open_the_door_to_monolith_management |
| sar_start_open_the_door_to_monolith_management | Пора со всем покончить! | _sarcofag | renamed (sar_monolith_destroy / sar_secret_lab / sar_warlab / sar_monolith) | gives con_start_sneak_into_t | kept: gives con_start_sneak_into_the_control_room |
| aes_1_start_go_to_sarcofag | Пора в центр Зоны! | _stancia_1 | renamed (rad_get_to_aes / bar_radar_deactivate (go to the center)) | gives sar_start_get_to_the_m | kept: gives sar_start_get_to_the_monolith |

### Update: Cordon after the flash drive (patch cordon, 2026-10-21)
Hidden in addition (coop_hidden_tasks.ltx): `esc_start_talk_to_the_sidorovich_quest_1_task` (helicopter), `esc_start_talk_to_the_fox_quest_1_task`, `esc_start_talk_to_the_fox_quest_2_task`.
Their completion only gave the next of these three, so no silent runner is needed; the infos they stood for are set silently by the dialogs (see `patches/cordon/NOTES.md`).
`esc_start_5_bottles_of_vodka_for_kuznetsov_quest_task` stays hidden (SoC has no task for the bridge pass), but its title and description now read "Pass the army outpost: 500 rubles".
The Kuznetsov `go_to_fox_2` dialog line was removed from `character_desc_coop_l01_escape.xml` (the pass is paid in `go_to_fox_1`).
Кратко (RU): три задания Акаси после флешки (вертолёты, Лис) больше не выдаются; проход через мост стоит 500 рублей как в ТЧ.

### Offline checks and tests
- `python tools/check_conflicts.py ...` (no new conflict), `python tools/check_lua_escapes.py`, `python tools/luabal.py` on the changed scripts, `python patches/repeatable_quests/tools/check_rq.py patches/repeatable_quests --mod <mod source>`
  (every job has section, task section, eng + rus strings, offer / accept phrases on an NPC, a hand-in path with dialog-level precondition, icons, no generic task menu on any NPC, hidden ids exist),
  `python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` stays BUDGET OK.
- `python tools/gen_fetch.py --check-items <base game configs> <mod configs> <stage gamedata\configs>`: every item section and reward item of the table exists (0 missing).
- `python patches/repeatable_quests/tests/rq_dialogs_mock_test.py` (needs lupa, no game): the REAL `coop_rq_dialogs.script` in a Lua VM with a mock engine against an independent model of the SoC rule: offers per giver and kind (lowest priority,
  none while one runs, gates, cooldown) for hand-made scenarios and 3000 random flag states, hand-in only with a running job AND the item (either twin), pay takes ONE piece, money + every reward item, item rewards off, no payment without the item (783 checks).
- Game test (listen host, 1 process, Cordon start; no talk window, no travel): `tests/rq_fetch_hooks.lua` calls the functions the dialog phrases use (precondition / action of `coop_rq_dialogs.script`, first speaker = the local player, second speaker = a friendly
  stalker spawned next to him), sets the flags the phrases set, gives items, and asserts (one assert per step): Sidorovich on his level with the PDA task, the giver icon and the offers while a job runs / after it is done / with the gate flag; then EVERY fetch job of the ltx
  (Bar, Yantar, Military jobs too, they only lack the PDA task, which needs their own level): hand-in precondition true, pay, item taken, money paid to the talking player, every reward item, hand-in closed, cooldown flag set.
  The first version opened the talk window and failed at "talk window opens at sidorovich is_talking=false" (nobody online / window not opened); it no longer depends on it. Not run in a game yet (offline only: the hook ran against a stub
  of the test library and the real dialog script, 188 asserts, 0 failed). Command line: see the header of the hook.

## Кратко по-русски
Весь видимый текст патча (реплики диалогов, названия и описания заданий в КПК, подписи меток на карте) теперь берётся из строк
`st_coop_repeat_quests.xml`. Раньше русский файл был копией английского, поэтому русские игроки видели английский текст. Теперь в нём 201 строка
настоящим русским языком в духе SoC (Сидорович, Волк, Бармен, Долг, Сахаров говорят каждый по-своему; типы заданий как в SoC:
"Уничтожение лагеря", "Защита лагеря", "Найти предмет", "Убить"). Остальные патчи с текстом уже были переведены. Проверено в игре на русском и
английском: подтянулись все строки (201), окно разговора с Сидоровичем показывает "Есть для меня работа?".

Дополнение (позиции целей): задания (убить, лагерь, защита, найти предмет) раньше создавали цели в одном заданном смарт-террейне, а на Бару это
обжитые места рядом с Баром и Долгом, поэтому бандитов Изи убивали за секунды. Теперь у каждого задания есть `site` (вершина графа игры):
цели создаются там, вне баз, безопасных зон и выходов с уровня (минимум 85 м до обжитых смартов, в основном 100-220 м), и не привязаны к смарту,
так что остаются на месте. Задание по-прежнему засчитывается, когда цели мертвы (кто бы ни убил), как в SoC. Проверено на Баре (задание Изи):
цели на месте, живы через 60 с, метка на карте на них. Таблица "было / стало" по всем 28 заданиям выше.

Дополнение 2: точки спауна теперь узлы AI-карты (x, y, z, level vertex, game vertex) вдали от аномалий, мин и радиации (на Баре таких мест всего четыре,
поэтому задания делят их по фракции целей). Метки на карте: у каждого задания своя подсказка (название и краткое описание, строка `rq_spot_<задание>`),
метка рассылается всем клиентам (`map_sync_spot`) и убирается без проверки `has_spot` при любом завершении (цели убиты кем угодно, сдача, отмена, таймаут).
Проверка в игре: Кордон, 6 заданий, 41 из 42 проверок прошли (лагерь Сидоровича: высота 8,2 м, не доказан, место заменено); Бар, 19 заданий, 131 из 133 проверок
(две пограничные: высота 4,3 м у bar_kill1 и разброс 6,3 м у hun_camp). Тест меток на выделенном сервере с клиентом: метка доходит до клиента,
убирается при сдаче и отмене, но оставалась на клиенте после гибели целей; исправлено (`sim_squad_scripted_cl_manager.dscript`), повторная проверка и
Ясень не прошли: после теста Бара драйвер видеокарты сбрасывался ("GPU device instance has been suspended").

Дополнение 3 (итог проверки 2026-10-21): метки на карте проверены на выделенном сервере с реальным клиентом: метка появляется у клиента после принятия
задания и исчезает при гибели целей (реальный убой), при удалении отряда, при сдаче предмета, при отмене и после загрузки сохранения (клиент подключается
после загрузки и видит метку, после убийства целей она пропадает). Кордон и Бар: старые "провалы" (8,2 м, 4,3 м, разброс 6,3 м) были замером через 5 секунд,
когда цели уже бежали по склону к игроку; теперь высота и разброс меряются в первый тик, когда цель появилась онлайн (Кордон: 0,7 м, Бар: до 0,9 м, разброс
стаи мутантов до 4,5 м), поэтому места не менялись. Ясень: 22 из 23 проверок; задание `rq_sak_find` не прошло "нет NPC ближе 80 м" (зомби в 36 м, патрульный маршрут
зомби проходит в 13 м от места). Найдено лучшее место (-252.0, -18.9, -42.7, 71, 1690), в `tests/batch_yan.lua` оно уже стоит, в `coop_repeat_quests.ltx` пока нет:
повторный запуск не состоялся, у ПК закончилась виртуальная память (30,8 из 31,5 ГБ без игр). Полный новый прогон батчей Кордона и Бара тоже не состоялся.


## Кратко по-русски (v1.4: задания «принести», меню заданий мода убрано, значки, сдача, аудит заданий)
- Меню «Мне нужна работа, что есть на примете?» (не наше и не из ТЧ, сделано автором уровней: «Найти артефакт / Убить сталкера / Зачистить местность от мутантов / Найти часть мутанта») убрано
  у Сидоровича, Бармена, Сахарова и Круглова: строка диалога закомментирована в `character_desc_*.xml` этого патча, общие файлы диалогов не тронуты. Уже взятое задание из этого меню
  можно сдать/отменить (диалоги сдачи и отмены оставлены). «18 заданий артефакт/часть, которые ничего не спаунят» были как раз из этого меню, а не из наших диалогов.
- Добавлен весь набор заказов ТЧ на артефакты и части мутантов (`task_manager.ltx` Steam-версии: `tm_find_artefact_*`, `tm_monster_part_*`, `barmen_*`, `ecolog_*`, `freedom_monster_part_1`): 23 заданий (Сидорович 5, Бармен 7, Сахаров 10, Лукаш 1).
  Заказчик, предмет (артефакт или его двойник `_soc`), награда, приоритет, тексты (название, речь заказчика, описание в КПК, «Я берусь.») оригинальные из ТЧ; награду и предметы получает игрок, который сдаёт, предмет берётся у него же.
  Те же строки меню «Есть для меня работа?», что и у заданий убить / лагерь / защита. Как в ТЧ (`CRandomTask:task_avail`) заказчик показывает по виду (артефакт / часть мутанта) только доступный заказ с наименьшим приоритетом,
  пока заказ вида выполняется, другой того же вида не предлагается, выполненный возвращается через 24 игровых часа; заказы с сюжетным условием открываются по ходу сюжета (флаги мода вместо инфо ТЧ). Меню не растёт:
  Сидорович до 5 строк, Бармен до 7, Сахаров до 5, Лукаш 1. Не включён заказ «Ночная звезда» у Сидоровича (в ТЧ нужен диалог про документы X18 у Сидоровича, которого в моде нет; награды `outfit_stalker_m2` нет ни в ТЧ, ни в моде).
  Таблица заданий: `tools/gen_fetch.py` (он же генерирует файлы), оригинальные тексты: `tools/fetch_texts.json`.

  | задание | заказчик | заказ ТЧ | название (ТЧ) | награда | когда предлагается |
  |---|---|---|---|---|---|
  | rq_sid_art1 | Сидорович (Кордон) | tm_find_artefact_1 (приоритет 1) | Найти артефакт «Медуза» | 1500 RU и бутылка водки | сразу |
  | rq_sid_art2 | Сидорович (Кордон) | tm_find_artefact_2 (приоритет 2) | Найти артефакт «Каменный цветок» | 3000 RU и бутылка водки | сразу |
  | rq_sid_art4 | Сидорович (Кордон) | tm_find_artefact_4 (приоритет 3) | Найти артефакт «Ломоть мяса» | 2500 RU и 3 армейские аптечки | сразу |
  | rq_sid_part1 | Сидорович (Кордон) | tm_monster_part_1 (приоритет 2) | Принести челюсть кровососа | 3000 RU и 5 коробок патронов 12x76 «Дротик» | после получения военного кейса (SoC agroprom_military_case_have, флаг AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO) |
  | rq_sid_part2 | Сидорович (Кордон) | tm_monster_part_2 (приоритет 1) | Притащить хвост псевдособаки | 1500 RU и 5 коробок патронов 12x76 «Дротик» | сразу |
  | rq_bar_art1 | Бармен (Бар) | barmen_find_artefact_1 (приоритет 1) | Найти артефакт «Ломоть мяса» | 2500 RU и 2 научные аптечки | сразу |
  | rq_bar_art2 | Бармен (Бар) | barmen_find_artefact_2 (приоритет 3) | Найти артефакт «Кристальная колючка» | 2500 RU, 2 научные аптечки и 2 антирада | после сдачи документов X18 Бармену (SoC bar_darklab_document_done) |
  | rq_bar_art3 | Бармен (Бар) | barmen_find_artefact_3 (приоритет 4) | Найти артефакт «Ночная звезда» | бронекостюм «Берилл-5М» и 3 гранаты Ф-1 | сразу |
  | rq_bar_art4 | Бармен (Бар) | barmen_find_artefact_4 (приоритет 2) | Найти артефакт «Вспышка» | 5000 RU | после сдачи документов X18 Бармену (SoC bar_darklab_document_done) |
  | rq_bar_art5 | Бармен (Бар) | barmen_find_artefact_5 (приоритет 5) | Найти артефакт «Золотая рыбка» | LR-300, подствольник M203, прицел SUSAT и глушитель | после выхода из лаборатории X16 (SoC yan_kill_brain_done, вместо него флаг X16_START_GET_OUT_OF_THE_LAB_TASK_INFO) |
  | rq_bar_part1 | Бармен (Бар) | barmen_monster_part_1 (приоритет 1) | Достать глаз «плоти» | 500 RU и 3 банки тушёнки | сразу |
  | rq_bar_part2 | Бармен (Бар) | barmen_monster_part_2 (приоритет 2) | Принести копыто кабана | 1500 RU | сразу |
  | rq_sak_art1 | Сахаров (Ясень) | ecolog_find_artefact_1 (приоритет 3) | Принести артефакт «Огненный шар» | артефакт «Плёнка» | сразу |
  | rq_sak_art2 | Сахаров (Ясень) | ecolog_find_artefact_2 (приоритет 1) | Найти артефакт «Грави» | 5000 RU и научная аптечка | сразу |
  | rq_sak_art3 | Сахаров (Ясень) | ecolog_find_artefact_3 (приоритет 2) | Добыть артефакт «Медуза» | 2500 RU и научная аптечка | сразу |
  | rq_sak_art4 | Сахаров (Ясень) | ecolog_find_artefact_4 (приоритет 4) | Достать артефакт «Лунный свет» | 10000 RU и 3 научные аптечки | сразу |
  | rq_sak_art5 | Сахаров (Ясень) | ecolog_find_artefact_5 (приоритет 5) | Достать артефакт «Морской ёж» | комбинезон «СЕВА» | сразу |
  | rq_sak_part1 | Сахаров (Ясень) | ecolog_monster_part_1 (приоритет 1) | Принести часть тела снорка | 2500 RU и научная аптечка | сразу |
  | rq_sak_part2 | Сахаров (Ясень) | ecolog_monster_part_2 (приоритет 2) | Добыть глаз плоти | 1000 RU и прицел SUSAT | сразу |
  | rq_sak_part3 | Сахаров (Ясень) | ecolog_monster_part_3 (приоритет 3) | Достать кабанью ногу | 2000 RU и 3 коробки патронов 12x76 «Дротик» | сразу |
  | rq_sak_part4 | Сахаров (Ясень) | ecolog_monster_part_4 (приоритет 4) | Найти хвост псевдособаки | 3000 RU и научная аптечка | сразу |
  | rq_sak_part5 | Сахаров (Ясень) | ecolog_monster_part_5 (приоритет 5) | Добыть челюсть кровососа | 6000 RU и научная аптечка | сразу |
  | rq_fre_part1 | Лукаш, лидер «Свободы» (Армейские склады) | freedom_monster_part_1 (приоритет 1) | Принести кабанью ногу | 1000 RU и бутылка водки | сразу |
- Строка сдачи теперь видна только пока у говорящего игрока есть взятое задание этого NPC и нужный предмет (раньше показывалась всегда). Шустрый больше не даёт заданий: задание про «Форт» перешло к Волку.
- Значки заданий: вместо вопросительного знака значки ТЧ из `ui_iconsTotal` (лицо Сидоровича, Бармена, учёного; для остальных значок типа задания).
- Аудит заданий мода против ТЧ (таблица выше): скрыты навсегда (не выдаются) только те, которых нет в ТЧ и от которых ничего не зависит: «Начало начал», «Отдохнуть на службе», «Спасение Лиса», «Спасти Юрика»,
  «Поговорить с Юриком», 3 шага «Замеры начались» и 3 «Замеры прерваны». Остальные задачи мода, которые выдают следующее задание цепочкой, оставлены (скрыть их без «тихого» исполнителя нельзя, не проверить без игры).

## Border fix (FOSTER, v1.4: "all bandits of the repeatable jobs ended up outside the map", also the patrol "on the road south of the checkpoint")
Cause: the v1.4 sites were picked from the whole AI map of the level. On Cordon that map covers the whole bounding box, the playable area is only the
fenced funnel: `rq_sid_camp`, `rq_sid_defend`, `rq_wolf_camp1` lay behind the barbed wire, `rq_sid_kill` south of the army checkpoint (its barrier is a wall of
missing nodes). On the Bar all 19 sites (north blob) lay beyond the level exits (`bar_mil` / `bar_ros` changers), on Yantar `rq_sak_camp2` beyond `yan_ros`.
The squads were created there and stood outside, so players saw them through the fence and the map spot pointed outside.
Fix: all 28 `site =` lines were re-picked among nodes of the playable area only (same rules as before: 80+ m from inhabited smart terrains / exits, 60 m
from safe zones, anomaly clearance relaxed on the Bar where the playable part is small). Playable area = nodes with at least 2.5 m clearance (Cordon) to a
missing node, 40 m around every level changer cut, the component of the hub; a site must also be 25 m (Cordon) / 6 m (Bar, Yantar) inside its exterior.
The Bar jobs now share the south road spots (276 1 -89), (290 3 -147), (276 0 -65), (238 2 -118), dogs (204 3 -144): hostile factions of jobs that run at the
same time can meet there. The boar / flesh den jobs no longer sit at their den (it is outside the exits) but on the road.
Tool: `tools/check_sites.py --ai-dir <dir with esc.ai bar.ai yan.ai> [--selftest]` (needs numpy + scipy; level.ai files from `coop.addon` via `get_ai.py`
style extraction): every site of the ltx must be inside, `--selftest` requires the old v1.4 sites (incl. the south-of-checkpoint patrol) to be rejected.
Result: 28 of 28 PASS, selftest 8 of 8 rejected.
Stay-put: a squad without a smart terrain asks `sim_board:get_squad_target`; for bandits that returns the squad itself (smart terrains have props 0 in
this mod) unless an actor is within 10 m, but predatory mutant squads can hunt vegetarian squads (350 m by day) and walk off. `create_squad_at` and the
monitor now flag the squads `rq_stay`, and `coop_repeat_quests.script` wraps `sim_board.get_squad_target` (once per level, pcall) to answer the squad itself for
flagged squads. Not shown in a game run (offline only): test `tests/rq_stay_hooks.lua` (Cordon, listen, accept `rq_wolf_camp1`, 180 s at time factor 60,
members within 40 m of the site, map spot on the squad); the command is in the hook's header.

## Job squads on a site: guard logic and loose ring (Forest35, v1.4.3: "bandits stand in a crowd in an open field and do not see you until point blank")
Cause: a squad made by `create_squad_at` has no smart terrain, so its members never got a job. `xr_logic.initialize_obj` read the empty custom data and
activated section `nil`: no scheme, no state manager stance, no facing. All members also stood on the one level vertex of the site (`db.spawned_vertex_by_id`
is set to it by `add_squad_member` and moves them there on every online switch), all facing the same way, so a player coming from the side or behind was only
noticed when close. Vision itself was never touched (no combat_ignore, no danger override; stock `xr_combat_ignore` is the same as SoC).
Fix: `spread_members` puts each member on a loose ring 4 to 7 m around the site (AI map nodes, each facing outwards), and `install_stay` also wraps
`xr_logic.initialize_obj` once per level: human members of a squad flagged `rq_stay` get `misc\rq_job_logic.ltx` (stock `remark` scheme, SoC `guard` stance).
Danger, combat, hit and combat_ignore stay the stock generic schemes. Server side, per squad, pcall guarded (any failure keeps the old behaviour).
Not shown in a game run (offline only).

## Guards look about (tester: "they just stand kind of still, it is weird")
Cause: `remark` (xrMPE xr_remark.script) calls `state_mgr.set_state(npc, anim, cb, 0)` ONCE (no `target` is given, so no look point) and then does nothing
(state_animation, `execute` only runs `update`). The stance is `guard` (rifle up, `idle` animation) and the look stays the engine default `look.danger`
(straight along the body). Nothing ever turns the head: a statue ring. SoC schemes that look alive call `state_mgr.set_state(npc, state, nil, nil,
{look_position = p})` again and again: `camper` scans the points of its `path_look` flags, `kamp` looks at its fire / the performer, `walker` at its `path_look`
points. All of them need patrol paths of the level (`patrol(name)`), and a job squad has none (only a site position), so none can be used as is.
Fix: `look_around` in `coop_repeat_quests.script` (called from `monitor` for every squad of an active job, pcall guarded): every 6 to 14 s each member that still
runs `remark@rq_guard`, has no enemy and no danger gets `state_mgr.set_state(obj, "guard", nil, nil, {look_position = p})`, p = 14 m away within 100 degrees of
his first facing (the outward direction `spread_members` gave him). Same call and same stance as camper/kamp, no new scheme, `rq_job_logic.ltx` unchanged.
Not used: `kamp` at a fire (no campfire object within 15 m of a Cordon or Bar site, checked against all.spawn; `xr_kamp` of `patches\campfires` does take
`center_pos`, so it would work where a fire exists); `camper` (needs `path_walk` AND `path_look` that exist in all.spawn).
Not shown in a game run (offline only). A member that is offline (no player near) is not simulated, so nobody looks anywhere then.
