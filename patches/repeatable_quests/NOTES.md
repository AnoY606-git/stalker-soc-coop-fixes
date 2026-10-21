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
  arrived. Cordon (6 jobs) first run: 41 of 42 checks PASS; the failure was `rq_sid_camp` (site y = 34 on a hillside: the squad was 18 m off
  the vertex height online), the site was replaced by a flat one near the bandit camp (97 13 612); two further jobs lost their targets only
  because the bandits killed the test player (god mode was not on; the batch now sets `g_god`).
  Not yet run on the final sites (the PC was out of memory): the Bar batch (19), the Yantar batch (3) and the Cordon re-run.

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
- Test `tests/rq_spot_hooks.lua` (dedicated server + two real clients, Cordon): for three jobs (targets removed by others, hand-in done flag,
  cancel / fail flag) each client must show the spot (`level.map_has_object_spot`) after the job was accepted and must not show it after the job ended;
  the bot also logs the hint text handed to the engine. Not yet run: the PC was out of memory (see below).

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
Проверка в игре: Кордон, 6 заданий, 41 из 42 проверок прошли, одно место (лагерь Сидоровича) заменено; Бар, Ясень и тест меток с двумя клиентами не успели
(на ПК не хватило памяти), команды запуска в `tests/`.
