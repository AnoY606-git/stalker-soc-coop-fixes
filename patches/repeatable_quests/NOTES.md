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
