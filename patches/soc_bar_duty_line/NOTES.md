# Bar Duty / Freedom line of the original SoC (patch soc_bar_duty_line)

Request (maintainer FOSTER): the quests must match the original SoC. `patches\bar_soc_quests` (phase 2) listed the Duty / Freedom line as "not implementable without new NPCs and items". This patch adds the NPCs (created by script at the SoC positions), the items, the dialogs, the tasks and the server tick. Read it with `patches\bar_soc_quests\NOTES.md` (the table of its last section is the state before this patch).

## What the retail SoC really has (Steam SoC 1.0006: dialogs_bar.xml, tasks_bar.xml, bar_dialogs.script, bar_rostok_tasks.script, all.spawn, gulag_bar.script)
* **Join Duty** (`bar_dolg_community_quest`): a gate guard sells the pass for 1000 (`bar_dolg_base_guard_acces`, infos `bar_dolg_base_pass`, `bar_dolg_community_start`), Voronin (`bar_dolg_leader_join`) orders the Bulldog 6 from Freedom (`mil_freedom_rg6_task`: Cook, vodka, the RG-6 in a stash `Mil_RG6`), the hand-in (`bar_dolg_leader_quest_rg6_finish` / `bar_dolg_leader_start` 31 / 311) gives the Duty suit, the oath (`bar_dolg_leader_prisyaga`, 9 phrases) calls `dialogs.actor_set_dolg`.
* **Cut content in the retail game** (found while reading the files, so these parts could only be rebuilt, not copied): the task `bar_dolg_test_quest` has no dialog, no item (`dolg_arhive_documents` is defined nowhere) and its strings `bar_dolg_win_on_arena` / `bar_dolg_return_to_ivancov` do not exist; `bar_bar_barmen_jobs` / `bar_bar_barman_veterans_finish` / `bar_bar_barman_killer_ambush` call `bar_dialogs.have_lucky_pda`, `give_lucky_pda`, `have_bar_tiran_pda`, `give_bar_tiran_pda`, `have_tiran_reward`, `have_svoboda_leader_reward` which are missing in the scripts; the items `bar_lucky_pda` / `bar_tiran_pda` have no name strings; all.spawn has the camp paths (`bar_evil_veterans_*`, `bar_ambush_killer_*`, `bar_spy_freedom_*`) but no smart terrain of the gulag types `bar_evil_veterans` / `bar_killers_ambush` and no story id `bar_crazy_veterans_leader` / `bar_svoboda_ambush_tiran`; nothing sets `bar_kill_svoboda_leader_start`. The patch finishes these chains with the smallest invention (marked "authored" below; every authored line is in `tools\duty_model.py` `AUTH`).

## What was added
| Part | Files |
|---|---|
| Script (flags, tick, NPC / item upkeep, dialog states and actions, PDA archive) | `scripts\coop_soc_duty.script` (+ `coop_scn_soc_duty.script` loader, `coop_soc_duty_say.script` generated) |
| 13 dialogs (103 phrases, SoC ids, SoC English + Russian text) | `configs\gameplay\dialogs_coop_soc_duty.xml` |
| 10 new characters + profiles | `character_desc_coop_soc_duty.xml`, `npc_profile_coop_soc_duty.xml` |
| spawn sections of the NPCs + the two PDA items | `configs\creatures\spawn_sections_coop_l06_rostok.ltx` (the mod's file + one block, nobody else ships it) |
| 6 tasks | `configs\misc\tm_coop_soc_duty.ltx` |
| logic of the NPCs | `configs\scripts\coop_l05_bar\soc_duty_stand.ltx`, `coop_l06_rostok\soc_vet_stand.ltx` |
| texts (110 strings, eng + rus) | `configs\text\eng|rus\st_coop_soc_duty.xml` |
Size: **0.11 MB raw, no model, texture or sound** (every visual is one the mod already uses: `stalker_dolg_3/4`, `stalker_bandit_1/2/4`, `stalker_merc_2`; the PDA item uses `dev_pda.ogf` of the Vasiliev PDA). No .ogf is shipped, so no capture ltx can be missing.

### NPCs (server `alife():create`, the pattern of patch cordon_technician, once per save: story id + a `SOC_DUTY_NPC_<KEY>` flag, AI node and game vertex looked up at run time)
| NPC | Level | Position | Source of the position |
|---|---|---|---|
| gate commander (Sergeant Plichko, story `bar_dolg_guard_commander`) | Bar | 191.87 0.0 104.53 | SoC all.spawn `bar_dolg_regular_5` |
| Captain Ivantsov (story `bar_dolg_captain_ivancov`) | Bar | 192.91 0.0 117.22 | SoC all.spawn `bar_dolg_ivancov` |
| Lucky (story `bar_crazy_veterans_leader`) + 2 veterans | Wild Territory | -250.7 1.2 14.7 / -247.3 0 7.0 / -245.3 0 15.4 | SoC paths `bar_evil_veterans_leader_walk`, `_guard_1_walk`, `_guard_2_walk` |
| Tyran (story `bar_svoboda_ambush_tiran`) + 2 Mercs, only while the Tyran job is open | Wild Territory | -234.3 9.36 49.0 (+ two spots 3 m away) | SoC smart terrain `ros_smart_stalker_killers1` |
| the two ambush snipers of the way, only while the Tyran job is open | Wild Territory | -204.0 0 63.7 / -187.7 0 139.7 | SoC all.spawn `bar_spy_killer_2`, `bar_spy_killers_2` (spawner condition `bar_kill_svoboda_ambush_start`, the same here) |
The commander and Ivantsov are invulnerable (like the mod's Duty leaders) and stand (`remark`, `guard`). The hostile ones stand guard and get the relation "enemy" to every player (server, every 5 s, online objects only). Their weapons / voices / names are the SoC ones where the mod has the section (Walther, LR300 in SoC; here the mod's own Abakan M2 / HPSA / L85 / USP lists), their portrait is the generic `ui_inGame2_neutral_0_3` (no new icon). Voronin and Petrenko are the mod's NPCs and only get the SoC dialogs.

### Dialogs (state from shared flags only, the NPC speaks first; every phrase that gives a flag carries it itself, so a cut-off talk loses nothing)
| Dialog id | SoC source | Speaker | Notes |
|---|---|---|---|
| `bar_soc_vo_dialog` | `bar_dolg_leader_start` (11 / 21 / 31 / 311 / 3111 / 41 / 51 / 81) | Voronin | 8 states; 31 / 311 / 3111 = the Bulldog 6 hand-in, outfit; 51 gives the Freedom leader order, 81 the praise |
| `bar_soc_vj_dialog` | `bar_dolg_leader_join` | Voronin | the Bulldog 6 job (accept gives `BAR_SVOBODA_RG6_START`) |
| `bar_soc_vp_dialog` | `bar_dolg_leader_prisyaga` | Voronin | the oath (9 phrases); here only after Ivantsov's reference (SoC descr: "the approval of one of the most respected fighters") |
| `bar_soc_vr_dialog` | `bar_dolg_leader_quest_rg6_finish` | Voronin | the hand-in as an actor dialog |
| `bar_soc_vb_dialog` | `bar_dolg_leader_job` | Voronin | after the oath |
| `bar_soc_pe_dialog` | `bar_dolg_petrenko_start` | Petrenko | greetings 11 / 21 / 31 |
| `bar_soc_gc_dialog`, `_gt_`, `_ga_` | `bar_dolg_base_guard_start`, `_talk`, `_acces` | gate commander | in SoC the pass is sold by the generic Duty "regular" guards; here by the commander (the mod's Duty walkers have their own dialogs) |
| `bar_soc_iv_dialog` | `bar_dolg_ivancov_start` (11 / 21 / 31) + **authored** I1 / I2 / I3 (offer, accept) and I5 / I6 (report) | Ivantsov | the test offer is the task text of SoC turned into speech: arena instead of the folder (the folder is defined nowhere in SoC) |
| `bar_soc_bj_dialog` | `bar_bar_barmen_jobs` (321 ... 32113, 271, 331 ... 33131, 311) | Barkeep | gate: the Agroprom hand-in of soc_dv_x18_quests (SoC `agroprom_military_case_done`) instead of `bar_rescue_research_start`; veterans first, Tyran after |
| `bar_soc_bv_dialog`, `bar_soc_ba_dialog` | `bar_bar_barman_veterans_finish`, `bar_bar_barman_killer_ambush` | Barkeep | PDA taken, **reward 5000 (Lucky) / 8000 (Tyran) is this patch's** (the SoC functions are missing) |
English voice: none. The Steam archives hold no recorded dialog line for any of these NPCs (checked like soc_mil_quests did), so the dialogs are silent in both languages. Each phrase has a PDA archive line.

### Flags (SoC info names, upper case) and the chain
`BAR_DOLG_BASE_PASS`, `BAR_DOLG_COMMUNITY_START`, `BAR_DOLG_COMMUNITY_LEADER` (gate), `BAR_DOLG_VETERAN_START` / `BAR_ARENA_PSEUDODOG_DEFEATED` / `BAR_DOLG_VETERAN_DONE` (Ivantsov), `BAR_SVOBODA_RG6_START` / `MIL_SVOBODA_RG6_GAIN` / `BAR_SVOBODA_RG6_DONE` (rifle), `BAR_DOLG_COMMUNITY_LEADER_DONE` (oath), `BAR_KILL_VETERAN_START/KILLED/DONE`, `BAR_KILL_SVOBODA_AMBUSH_START/KILLED/DONE`, `BAR_KILL_SVOBODA_LEADER_START` / `MIL_KILL_SVOBODA_LEADER_KILLED` / `BAR_KILL_SVOBODA_LEADER_DONE`. New: `SOC_DUTY_*` bookkeeping (NPC made, PDA made / taken, RG-6 made). Read from others: the Agroprom hand-in flag (soc_dv_x18_quests), `MIL_SMART_TERRAIN_16_FREEDOM_1_SQUAD_DEAD` (Lukash dead, mod), `BAR_VORONIN_DEAD` (endings), the two arena pulses `BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_SQUAD_DEAD` and `..._DTT_...` (the arena restrictor sets and clears them within a frame, so the script polls them on every frame).

Chain: pass (1000) -> `bar_soc_dolg_community_task`; Ivantsov offers the test -> `bar_soc_dolg_test_task` (win the pseudodog fight, report); Voronin's job -> `bar_soc_rg6_task` (the RG-6 is created at the SoC stash `Mil_RG6` -274.55 -27.47 245.41 when the job is accepted and the party is on the Army Warehouses; the Cook / vodka chain is not in the mod, so the rifle lies in the stash; map marker through the story id) -> hand-in (rifle taken, Duty scientific suit given) -> oath (needs the reference) = `actor_set_dolg` of the talking player. The Barkeep: veterans (`bar_soc_veterans_task`: Lucky dies -> his PDA is made at the body -> Barkeep, 5000) then Tyran (`bar_soc_ambush_task`, 8000). After Tyran Voronin orders the Freedom leader (`bar_soc_leader_task`: Lukash dies -> report, Voronin 81).
Soft-lock rules: a dead gate commander gives the pass; a dead Ivantsov gives the reference; a dead Voronin (or `BAR_VORONIN_DEAD`) ends the line; Lucky / Tyran dead for any cause = killed, the PDA is made once at the body (or next to a player when he never existed: three failed creations count as dead) and replaced when it is gone; the PDA / RG-6 hand-ins also open to the talker when a player held the item once and nobody carries it any more (holder died); a lost RG-6 / PDA is replaced next to a living player; every task goes to every living player once per session (late joiners, respawns).

## What is still impossible and why
* **Duty territory rules**: no `bar_dolg_territory` / kill / warn zones, `bar_dolg_base_rules` is never given even in SoC (`bar_dolg_base_guard_rules` stays unused), the bunker guard dialog `bar_dolg_guard_bunker_start` (the bunker guards are the mod's squad members with their own dialogs).
* **Cook / vodka chain** of the Bulldog 6 (`mil_cook_*`): the mod has no Cook and no vodka dialog chain.
* **Ivantsov's folder** (`dolg_arhive_documents`) and the Arena win as a hand-written objective: SoC has no item and no strings; the arena win depends on the arena restrictor's one-frame pulse (polled every frame, untested in the game; if the arena patch is skipped or the fight never ends in a win the oath stays closed, the rest of the line does not depend on it).
* **Duty membership** is `dialogs.actor_set_dolg` for the talking player: whether the engine propagates it to the other players of the party is closed code; the Freedom route of soc_mil_quests (Lukash) turns hostile for that player only if the engine applies it.
* **Zavskald rewards** (`bar_dolg_zavskald_reward`, S14 Thunder for Tyran, the suit for the leader): their functions do not exist in SoC.
* **English / Russian voice**: none exists. New NPC portraits are generic (no new icon).
* Not verified in the game: the creation of stalkers at the positions (the technician pattern is proven in the game, the positions are SoC's and the AI node is searched around them), their logic start, the hostile relation.
* Coordination: `soc_mil_courier` (new, no NOTES yet) reads Voronin's story id; Voronin's start dialog is now `bar_soc_vo_dialog`.
* **soc_mil_courier overlap (review fix)**: that patch builds the same Bulldog 6 job (Chef, vodka, the RG-6 at the same stash, Voronin's order and hand-in, the Duty suit). When its section `mil_soc_cook` exists in the loaded configs, this patch steps back: its Voronin job / hand-in dialogs are hidden, no RG-6 is created, task `bar_soc_rg6_task` is not given, and the flag `MIL_SOC_RG6_DONE` of the courier patch counts as the Bulldog 6 step (oath, community task). Without the courier patch the behaviour is as above (mock test section 7b).
* Review fix: Lucky / Tyran made by this patch and later released (no story id, no entity) count as dead, so the Barkeep job cannot soft-lock when the body is cleaned up.

## Shared files (done by `tools\apply_shared.py`, run it AFTER the zip; idempotent; tested on a copy)
| File | Change |
|---|---|
| `patches\repeatable_quests\...\system.ltx` | `dialogs_coop_soc_duty`, `character_desc_coop_soc_duty`, `npc_profile_coop_soc_duty` appended to the three lists |
| `patches\repeatable_quests\...\misc\task_manager.ltx` | `#include "tm_coop_soc_duty.ltx"` |
| `patches\repeatable_quests\...\gameplay\character_desc_coop_l05_bar.xml` | Voronin / Petrenko start with the SoC dialogs, Voronin + the Barkeep get the actor dialogs |
| `installer\changes_1.4.en.txt` / `.ru.txt` | the line below (before "Smaller patch file"); the sentence of the bar_soc_quests line that says the Duty / Freedom quests are not in the mod is removed |
| `patches\bar_soc_quests\NOTES.md` | pointer to this patch |
Planned changes line (the tag `@soc_bar_duty_line` drops it when the patch is skipped):
EN: `- @soc_bar_duty_line: The Duty / Freedom line of the Bar follows the original SoC. Duty's gate commander (Sergeant Plichko) and Captain Ivantsov stand where they stood in SoC; the commander sells the pass for 1000, Voronin, Petrenko and the commander speak the original lines. Join Duty: Ivantsov's test (win the pseudodog fight on the Arena), Voronin's Bulldog 6 job (the RG-6 lies in the Freedom village stash of the Army Warehouses), the oath and the Duty suit. The Barkeep's jobs "Kill the mad veterans" (Lucky and two veterans camp on the Wild Territory) and "Eliminate the Mercs" (Tyran with his men at the construction site, snipers on the way) end with their PDAs; after the Mercs Voronin sends you to kill the leader of Freedom (Lukash). Every task goes to every player, late joiners included; a dead NPC or a lost item does not block a step.`
RU: see `tools\apply_shared.py` (the `RU` string, same text).

## Offline checks done
* `python patches\soc_bar_duty_line\tests\mock_test.py`: 98 PASS (real script + real dialogs in a Lua 5.1 VM: pass with and without money, late joiner, the test, the Arena pulse latched after it is cleared, rifle created once at the SoC stash and only on the Army Warehouses, hand-in, outfit, oath gated on the reference, replacement of a lost rifle / PDA, hand-in when the holder died, dead commander / Ivantsov / Voronin, Lucky and Tyran creation and death, PDA once, rewards 5000 / 8000, creation failure counted as death, Lukash order and praise, hostile relation, 2000 random flag sets: exactly one Voronin and one gate state, at most one Barkeep job state).
* `python -I patches\soc_bar_duty_line\tools\check_duty_chain.py <mod source gamedata.db0> --shared <tree after apply_shared>`: 0 problems (13 dialogs, 103 phrases; texts in both languages, functions, say lines, characters / profiles / sections, tasks vs stages, NPC table vs model).
* `python tools\luabal.py` on the three scripts and the two hooks: OK. `python tools\check_lua_escapes.py`: nothing new (3 old literals). No em dash, no personal path (grepped).
* Build of a scratch copy (repo patches copied, `apply_shared.py` run on the copy twice: second run "nothing"): `python -I build.py <scratch>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`: verify_db 0 problems, **BUDGET OK** (db 53.7 MB, 14.4 MB headroom with the other patches of that moment); `check_conflicts.py` on the copy: only the 7 known overlaps, none of this patch.

## Game test (not run here; one test at a time, offline job for the coordinator)
```
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socduty -ExtraDir <stage>\gamedata -Hooks <repo>\patches\soc_bar_duty_line\tests\soc_duty_hooks.lua -SoakSeconds 300 -ResultDir <dir>
python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix SD
```
(`<stage>` = `build.py ... --stage=<stage>` after `apply_shared.py`.) The hook fast-forwards the flags and asserts on host and client: the six tasks with title and the description of the moment, each given to every player (`coop_soc_duty.who`), the dialog states, the spawn sections / items / texts in the loaded configs, the dead-NPC fallbacks. NPC part (commander and Ivantsov online at the SoC spots with an active logic, then Lucky and the veterans hostile, then Tyran and the Mercs after the job flag), two calls with `-Cfg dest=bar` and `-Cfg dest=ros`, `-Cfg no_respawn=1`, `-Clients 0`, `-Hooks ...\tests\soc_duty_npcs_hooks.lua`.

## Кратко по-русски
Линия Долга и Свободы на Баре сделана по оригинальной ТЧ.
- Новые НПС создаёт сервер скриптом на позициях ТЧ: командир ворот Долга (сержант Пличко) и капитан Иванцов на Баре; Счастливчик с двумя ветеранами (лагерь на Дикой территории); Тиран с наёмниками и два снайпера по дороге (только пока открыта работа "Тиран"). Воронин и Петренко получили оригинальные реплики.
- Вступление в Долг: пропуск за 1000 у командира, проверка Иванцова (победить псевдособаку на Арене), задание Воронина на РГ-6 (РГ-6 лежит в тайнике деревни Свободы на Военных складах, как в ТЧ), сдача, костюм Долга, присяга. Работы Бармена "безумные ветераны" (КПК Счастливчика, 5000) и "Тиран" (КПК Тирана, 8000); после Тирана Воронин посылает убить лидера Свободы (Лукаш).
- Каждое задание получает каждый игрок; смерть НПС или потеря КПК/РГ-6 цепочку не блокируют.
- Невозможно: зоны территории Долга, цепочка с Поваром и водкой, папка Иванцова (в ТЧ её нет), награды завсклада (функций нет в ТЧ), озвучка (записей нет). Часть диалогов Иванцова и награды Бармена написаны для патча (в ТЧ эти ветки вырезаны), см. раздел "Cut content".
- Размер 0,11 МБ, моделей и звуков не добавлено. Проверки: мок-тест 107 PASS, статическая проверка цепочки 0 проблем, сборка копии BUDGET OK. `tools\apply_shared.py` запускать после zip.

## Petrenko fix
Petrenko is a trader. His three greetings ended with dialogs.break_dialog (stop_talk), so the talk window closed at once and the Trade button was never reachable (Talk did nothing). The greetings now end without break_dialog, like the mod's own start dialogs (model flag keep_open in tools\duty_model.py).
