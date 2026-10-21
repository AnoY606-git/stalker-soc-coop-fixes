# Agroprom and Agroprom underground: the quest chain in the original SoC order (phase 2 of "quests must match the original")

Maintainer FOSTER: the quests themselves must be remade to match the original SoC. Phase 1 (`patches\soc_task_texts`) did the texts, this patch does the
structure of Agroprom (`coop_l03_agroprom`) and its underground (`coop_l03_agroprom_underground`).

## Sources
Steam SoC 1.0006 read with `tools\xdb_soc.py`: `tasks_agroprom.xml`, `info_l03agroprom.xml`, `dialogs_agroprom.xml`, `agroprom_tasks.script`, `xr_effects.script`
(`agr_krot_sos`, `agr_krot_sos_1_2`), `config\scripts\agr\agr_krot.ltx`, `agr_factory_assault_trigger.ltx`, `agr_krot_combat_trigger.ltx`, `escape_tasks.script`.
Russian wording: the SoC string table of the SoC add-on (`st_soc_strings.xml`), English: the Steam string tables (`tools\soc_agr_strings.json` holds the ids used here).

## What SoC does (short) and what the mod did
SoC: Seriy (Garbage dialog) starts `agr_meet_krot_band` ("Get information about Strelok": 1 meet Mole's group, 2 get the info). On the way a gunfire zone gives
`agr_help_stalkers` ("Help the stalkers"); when the assault is beaten, Mole's call gives `agr_help_krot` ("Save Mole"). Mole thanks you, walks to the well
and gives the stash route in a dialog (`agr_factory_krot_start`, info `agr_krot_secret_info`), which starts `agroprom_find_gunslinger_cache` (1 find the stash,
2 find the information about Strelok in it = take the flash drive, 3 find the way out). Taking the flash drive starts `agr_find_ghost` ("Find out what
happened to Ghost"), which ends on Yantar. The documents task `agroprom_get_military_documents` comes from the Trader on Cordon (objective 0), objective 1
steal the documents (Agroprom), objective 2 take them to the Barkeep.
Mod (level maker): the alarm stalker's call gave "Save Mole", both soldier squads dead gave "follow Mole" (a step SoC does not have), then "talk to Mole" (a separate
task), a dialog with invented lines, the stash as two tasks, the documents as two Agroprom tasks (given after leaving the underground) next to the Cordon one.

## Old chain vs new chain
| # | Mod before | SoC | New (this patch) |
|---|---|---|---|
| 1 | arrival: nothing; alarm stalker gives "Save Mole" (one player only, `give_task` effect) | `agr_help_stalkers` from the gunfire zone, `agr_meet_krot_band` from Seriy | arrival flag `AGR_STALKER_HELP_1_INFO`: "Get information about Strelok" (objective 1 text) and "Help the stalkers" for EVERY player (server tick) |
| 2 | "Save Mole" at once | `agr_help_krot` after the assault, from Mole's call | "Save Mole" (the SoC `agr_help_krot` text) for every player when Mole's call starts (camera flight flag `AGR_THE_ORDER_TO_KILL_STALKER_...`), or a player reached the yard, or the first soldiers fell |
| 3 | both squads dead: "follow Mole" task | none | gone. Mole's walker still waits for a player near him on the way and at the well (SoC: `remark@thank`, `walker@well`), no task for it |
| 4 | "talk to Mole" task | objective 2 of `agr_meet_krot_band` | the SAME task as 1: its description turns to "Get info from Mole" when Mole waits at the well (`AGR_START_FOLLOW_..._THE_AND_INFO`). The separate "talk" task is never given |
| 5 | Mole dialog with invented lines | `agr_factory_krot_start` (Seriy branch) | the same dialog, six lines replaced by the SoC lines (ids kept, so the PDA archive functions work); last phrase gives the route flag `AGR_SMART_TERRAIN_7_STALKER_MOLE_TALK_TO_THE_STALKER_MOLE_STOP_DIALOG_INFO` |
| 6 | "go down" task | `agroprom_find_gunslinger_cache` objective 0 | same task (route text), given to every player when the route flag is set |
| 7 | underground: task given by the arrival restrictor (one player), done when a client holds the flash drive; second task "return to the surface" | objectives 1, 2, 3 of ONE task | ONE task "Find Strelok's group's stash": objective 1 "Find the stash" (marker: the stash box), objective 2 "Find information about Strelok in the stash" when a player stands at the box (`AGRU_SOC_STASH_FOUND`, server tick, 7 m), objective 3 "Find the way out of the underground" (no marker, SoC hides it) once the flash drive is taken; done when the group is back on the surface (`AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO`) |
| 8 | nothing | `agr_find_ghost` | "Find out what happened to Ghost" for every player when the flash drive is taken (any level); done when Ghost's documents are taken on Yantar (`X16_GHOST_DOCS_TAKEN`, patch yantar_restore), or Yantar's main chain is done |
| 9 | documents: Cordon task + two Agroprom tasks, case spawned only after the underground | one task, objectives 1 and 2 | ONE task, the Cordon one (`esc_soc_military_documents_task`): text and marker follow the flags: Cordon text, "Steal the militaries' documents" once the group is on Agroprom (no marker), "Take the documents to the Barkeep" (marker: the Barkeep) when the case is in hand. The two Agroprom documents tasks are never given. The case now spawns when the first player enters Agroprom (the old spawn in the underground exit zone is a fallback, never twice: `AGR_SOC_DOCS_SPAWNED`) |

## Soft-lock rules (all server side, all tested offline)
* Mole dead (squad flag `AGR_SMART_TERRAIN_4_STALKER_MOLE_SQUAD_DEAD`, new `on_death` in `squad_descr_coop_l03_agroprom.ltx`) before the talk: the tick gives the route flag
  ("Mole's flash drive"), "Save Mole" fails, the first task completes, the way down is given. SoC would fail `agr_meet_krot_band` there.
* Taking the underground entrance without the talk still works (the arrival restrictor sets the route flag and the "arrived" flag, as before).
* The flash drive flag is also set by the server when any player carries `dev_flash_agru`, the stash flag when any player is at the box, the documents flag
  (`AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO`) when any player carries `agr_safe_container_1`, on any level. Nothing waits for a client task to notice.
* Every task of the chain is given by the server tick (`gamedata\scripts\coop_scn_agroprom_soc.script`, loaded on every level by the Scene Director) to every alive player,
  once per level load, only while its stage is open; a stage closes with the same condition that completes its task, so a finished task never returns. A late joiner gets
  the open stage. The stock `give_task` effects (restrictors, alarm stalker: they hand a task to ONE player and return) are removed from the Agroprom logic.

## Flags (names unchanged unless marked NEW)
Read by others: `AGR_STALKER_HELP_1_INFO` (Garbage task, cat scene), `AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO` (Garbage Gray restrictor), `AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO`
(Garbage Duty, repeatable quests gate, Cordon documents task), `BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO` (Cordon documents task). All still set.
NEW: `AGR_SMART_TERRAIN_4_STALKER_MOLE_SQUAD_DEAD` (squad death), `AGRU_SOC_STASH_FOUND`, `AGR_SOC_DOCS_SPAWNED`. Not in `story_flags_table`: the engine syncs flags by name (packet id 65535) and saves them.
Documents hand-in at the Bar (patch soc_dv_x18_quests): item section `agr_safe_container_1`, done flag `BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO`; the Ghost task does not need the flash drive item any more
(it is flag based), so the Barkeep may take `dev_flash_agru` without breaking anything here.
For the Yantar phase: the Ghost task is closed by `X16_GHOST_DOCS_TAKEN` or `YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO`; Yantar itself does not read any Ghost flag in the mod (its start is
the Sakharov / Kruglov chain), so nothing there changed. SoC starts Yantar's `yan_provodnik_spawn` from the Ghost PDA tip; that is a Yantar job.

## Files
| Patch | File |
|---|---|
| agroprom_soc | `configs\misc\tm_coop_l03_agroprom.ltx`, `tm_coop_l03_agroprom_underground.ltx` (made by `tools\make_agroprom_chain.py`), `squad_descr_coop_l03_agroprom.ltx`, `configs\scripts\coop_l03_agroprom\agr_smart_terrain_7_walker_alarm.ltx`, `scripts\coop_scn_agroprom_soc.script`, `configs\text\{eng,rus}\st_agroprom_soc_chain.xml`, `st_dialogs_coop_l03_agroprom.xml` (made by `tools\gen_agroprom_text.py`) |
| any_player_restrictors (edited in place) | `agr_stalker_help_space_restrictor.ltx` (spawns the case on first arrival), `agr_start_return_to_the_surface_task_end_space_restrictor.ltx` (spawn only if not yet, no give_task), `agru_go_to_the_agroprom_underground_end_space_restrictor.ltx` (no give_task) |
| cordon (edited in place, `tools\make_tm_coop_l01_escape.py`) | `configs\misc\tm_coop_l01_escape.ltx`: description / target condlists of `esc_soc_military_documents_task`; `tools\check_cordon_chain.py` reads condlist descriptions |
Mole's dialog file (`dialogs_coop_l03_agroprom.xml`, patch cordon_technician) is unchanged: same ids, flags and PDA functions, only the strings changed.

## Checks done offline
* `tools\check_agroprom_chain.py <mod source> --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`: 0 problems (every task of the tick has a section, no retired task is given, no give_task left in
  the Agroprom logic, all title / description ids of every condlist branch exist in eng and rus, every flag read has a setter, the flags other levels read still have setters, Bar dialog gives the done flag, Mole dialog functions / texts / flag, balanced condlists, the stash box and the level changer exist as story objects).
* `tests\agroprom_chain_mock_test.py` (needs `pip install lupa`): the REAL script in a Lua VM with an engine mock, 39 checks, 0 failed: every player once at the right stage, late joiners, closed stages, Mole dead fallback, documents flag on any level, stash / flash fallbacks, Ghost task on any level, dead players skipped.
* `tools\check_conflicts.py` (only the known overlaps), `tools\check_lua_escapes.py` (only old findings), `tools\luabal.py` on the script, `patches\cordon\tools\check_cordon_chain.py` 0 problems, `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK (headroom 22.6 MB).

## Game test (one listen-host run each, automated, nothing human)
Hook `tests\agroprom_soc_chain.lua` (picks its part by the level name; every client asserts its own task list, the server role asserts the tick served every player):
```
python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l03_agroprom -Mode listen -Clients 1 -Owner agrsoc -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\agroprom_soc\tests\agroprom_soc_chain.lua -SoakSeconds 150 -CompareTimeout 10 -ResultDir <dir>
python tools\stalker_xrmpe\qa_verdict.py <dir>
```
The underground part: the same command with `-Map coop_l03_agroprom_underground -Owner agrsocu`.

## Not proven / limits (honest)
* Nothing here ran in the game yet. Not verified: that the description / target condlists of a task (`{+FLAG} id, id`) work in this xrMPE build exactly as in the SoC engine (the code in
  `task_objects.script` / `task_functor.script` is written for it and the mod's own `condlist` lines use the same parser); the combined `{-FLAG} section %effects%, section` lines of the restrictors (the parser is the generic one).
* The mod has one fight (two soldier squads), SoC has two: "Help the stalkers" is closed by the first squad dead, "Save Mole" by both. Which squad stands where was not checked on the map.
* Mole is invulnerable in the level maker's logic, so a real death normally cannot happen; the fallback is driven by the squad death flag and tested with the flag.
* Not added: Seriy giving `agr_meet_krot_band` on Garbage (Garbage patches, the arrival flag gives it here as a fallback), the SoC voice lines of Mole's dialog, the tips (`tips_agr_krot_sos`, `ghost_tips`),
  the sold flash drive variants (`sell_krot_flash`), the `agroprom_find_stalker_phantom` variant (SoC never gives it in the normal game), the second documents map spot of SoC (the case is not a story object).

## Кратко по-русски
Агропром и подземелья теперь идут как в оригинале ТЧ: на входе у всех игроков появляются "Получить информацию о Стрелке" (встретиться с группировкой Крота) и "Помочь сталкерам";
после зова Крота - "Спасти Крота"; когда Крот ждёт у колодца, то же первое задание показывает "Получить информацию от Крота" (отдельного шага "следовать за Кротом" больше нет).
Крот говорит оригинальными репликами (диалог "agr_factory_krot_start") и называет дорогу к тайнику. Тайник - одно задание (найти тайник, найти информацию о Стрелке, выбраться), флешка запускает
"Узнать о судьбе Призрака" (заканчивается на Янтаре у тела Призрака). Военные документы - одно задание от Сидоровича (метка на кейсе, затем на Бармене), кейс лежит на Агропроме с самого входа.
Все задания получает каждый игрок (сервер), поздние игроки получают текущий этап; если Крот погиб, цепочка идёт дальше. Проверено офлайн (проверка цепочки, мок-тест 39 проверок); в игре не запускалось.
