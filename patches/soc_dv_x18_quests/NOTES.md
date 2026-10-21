# Dark Valley, lab X18 and the Barkeep's X18 job: the quest chain of the original SoC (phase 2)

Request (maintainer FOSTER): "the quests themselves must be remade to match the original SoC". Phase 1 (texts) is `patches\soc_task_texts`; its NOTES.md section "Phase 2" lists the differences. This patch does the structure for Dark Valley, X18 and the Bar side of that line (Barkeep job dialog). The rest of the Bar (X16 documents and Brain Scorcher jobs, hunter, Kruglov, Duty / Freedom line) is in `patches\bar_soc_quests` (it extends the Barkeep dialog, `coop_soc_bar.script` and `tools\apply_dialogs.py` of THIS patch).

## The original SoC chain (Steam SoC 1.0006: tasks_darkvalley.xml, tasks_bar.xml, info_l05dark_valley.xml, info_l06dark_valley_u.xml, info_l07rostok.xml, dialogs_bar.xml)
1. Sidorovich's military case job (patch `cordon`) -> task "Find the militaries' documents" -> the documents go to the BARKEEP.
2. Barkeep (`bar_bar_barmen_start`): "Have you brought the documents from the Institute?" -> hand-in, 5000 -> the same talk offers the job -> "I'll try." gives `bar_darklab_document_start` = task `bar_darklab_documents` "Find the documents in the underground lab", 4 objectives: Sneak into the base, Take the key to the lab from Borov, Get out of the bandit base, Find the entrance to the lab.
3. Entering the lab starts `bar_darklab_documents2` "Find the documents in X18": Find the documents, Bring the documents to the Barkeep. Finding them starts the soldiers' raid (`val_raid_start`) = task `val_come_to_trader` "Get out of the Dark Valley", which FAILS when the documents are done at the Barkeep.
4. Code doors `dar_codedoor_1/2`: objective 1 discover the code, objective 2 open the door using the code.
5. Hand-in to the Barkeep (`bar_darklab_document_done`): 10000, then his X16 job speech.
6. Side: `val_captive_help` (Bullet, two objectives) and `val_prisoner_help` (free the Duty member Serega from the bandit prison, given after the captive scene).

## Old (mod) vs new
| # | Mod (level maker) | New |
|---|---|---|
| 1 | Barkeep: three separate dialogs (`has_documents_agroprom`, `go_to_darkvalley` after a 30 s timer set by a restrictor, `1_has_documents_darkvalley`): 5 / 7 phrase monologues, no money for the documents | one SoC dialog `bar_soc_barmen_start_dialog` (Barkeep greets first, answers as in SoC, original wording EN + RU, original English voice): Agroprom hand-in (documents + flash drive taken, 5000), the X18 job offer in the same talk ("I'll try." / "No, I don't want to do it yet." and ask again later), the X18 documents hand-in (documents taken, 10000, flag set in the SAME phrase so a cut-off talk cannot lose the documents), the X16 job speech |
| 2 | task "kill Borov and take the card" (Bar), given by a restrictor, then "Find the documents" with the lab entrance as target | the four SoC objectives `val_soc_darklab_1..4_task` (title "Find the documents in the underground lab"); given by the server tick to every player |
| 3 | docs tasks 1, 2, 3 ("Find the documents" x3, per-player completion) | one SoC objective "Find the documents" (`val_start_sneak_into_the_x_18_lab_1_quest_task`, SoC `bar_darklab_documents2` objective 1) done when the party holds all three; the three level-maker steps are hidden |
| 4 | "show the documents to Sidorovich" (+ Sidorovich dialog, 1000, documents NOT taken) | removed (task hidden, dialog and its list entry deleted); "Bring the documents to the Barkeep" is SoC objective 2 |
| 5 | raid started when a poltergeist was dead and a player came out of the lab; "kill the flame poltergeist" and "To the exit!" tasks | raid starts when the documents are found (flag `BAR_DARKLAB_DOCUMENT_GAIN`, SoC `val_raid_start` on `bar_darklab_document_gain`) and a player comes out; both mod-only tasks hidden. `val_come_to_trader` (existing section `val_start_get_out_via_south_gate_quest_task`) now fails when the documents are at the Barkeep, like SoC |
| 6 | code doors: one task per door, given by a `give_task` in the door logic to the first player only | two steps per door (`x18_soc_codedoor_N_code_task` "Discover the code" done when the party holds the document with the code, then `x18_soc_codedoor_N_open_task` "Open the door using the code"); the door logic only sets `DAR_DOOR1_CLOSED` / `DAR_DOOR2_CLOSED` (SoC `dar_door1_closed`), the tick gives the tasks to everybody |
| 7 | SOS signal x2 (Lucky) and fake Gauss x2 tasks (5000 reward on the SOS escort) | tasks hidden (SoC has none); the NPCs, dialogs and flags stay. The 5000 task reward of the SOS escort is gone with the task |
| 8 | Serega in the bandit prison exists (squad `val_smart_terrain_20_duty_1_squad`, cell door opened by a switch) but no task | new SoC task `val_prisoner_help` (`val_soc_prisoner_task`, SoC text incl. the briefing): given when the captive's captors are dead (SoC: after the captive scene), done when the cell door opens (`VAL_VAL_DOOR_METAL_2_OPEN_INFO`), fails when Serega dies |
| 9 | Bullet: `give_task` from his walker logic, first player only | the walker logic sets `VAL_ESCORT_TASK_START`; the tick gives both objectives of `val_captive_help` to every player |
| 10 | the Barkeep job started 30 s after the hand-in through `bar_start_sneak_into_the_x_18_lab_quest_task_space_restrictor.ltx` | that restrictor is inert (the job starts in the dialog); the items the job gives (outfit, key card) are still given by `bar_give_item_scientific_outfit_and_dev_card_1_space_restrictor.ltx` on the flag the "I'll try." phrase sets |
| 11 | Yantar line `bar_start_go_to_yantar_quest_task` given to the first player by the hand-in task | given to every player by the tick once the documents are at the Barkeep (Rostok / Yantar restrictors unchanged) |

## How it works
`coop_soc_dv.script` (loaded by `coop_scn_soc_dv.script`, like every `coop_scn_*`): a server tick (1 s).
1. `progress()` derives the SoC infos from the world and makes the chain monotonic (a later info also sets every earlier one, so a skipped step never blocks): `VAL_ACTOR_ON_BANDITS_BASE` (a living player within 30 m of the base middle, level coop_l04_darkvalley), `VAL_ACTOR_HAS_BOROV_KEY` (Borov dead by anybody, or later steps), `VAL_ACTOR_LEAVE_BANDITS_BASE` (key taken and EVERY living player on the level farther than 75 m), `VAL_X18_DOOR_OPEN` + `DAR_RUN_QUEST` (lab entered, set by the lab restrictor `VAL_START_SNEAK_INTO_THE_X_18_LAB_1_QUEST_TASK_INFO`), the three document flags `X18_START_GO_TO_X18_DOC_N_TASK_INFO` (any player holds the item, same check as `xr_conditions.any_actor_has_item`), `BAR_DARKLAB_DOCUMENT_GAIN` (all three), `VAL_ESCORT_HELP_PRISONER_TASK`.
2. Every task whose stage is open is given to EVERY living player once (`GiveTaskToClient`, the stock `give_task` hands a task to the first player only), so late joiners and respawned players get all open tasks; finished stages are closed by flags, so they are not offered again.
All waits are shared story flags (saved, synced); task completion conditions use flags only, so nothing depends on which player holds what. A dead NPC never blocks a step: Borov dead = key step done, Bullet dead = his task fails, Serega dead = his task fails, the Barkeep is the only hand-in and cannot die in the safe zone.
Approximations (the mod's level has no SoC zones `val_zone_pipe` / `val_zone_exit_tunnel`): the base zones are circles (middle 36 / -70, 30 m in, 75 m out) around the objects of the bandit base (Borov's house, prison, base door). Positions come from the mod's all.spawn.

`coop_soc_bar.script`: state of the Barkeep (`agroprom` / `offer` / `wait` / `docs` / `default`, from flags only, mutually exclusive), hand-in helpers (the stock transfers and money helpers), PDA archive line per phrase, voice. Voice: the 7 Barkeep lines that have a recording in Steam SoC (phrases 2, 221, 151, 15111, 171, 1721, 17212) under `sounds\characters_voice\dialogs\eng\` (0.84 MB), played on the talking player's machine only, language = that player's `voice_language` (auto / rus / eng, `coop_soc_opening.voice_lang()` of `cutscenes_pkg_opening`), no subtitles. The original Russian recordings of the same 10 phrases (FOSTER's upload of the Russian SoC sounds) ship in patch `soc_ru_voices` at the stock path `sounds\characters_voice\dialogs\bar_bar_barmen_start_<id>.ogg`; with `rus` they play from the `rus` slot of the table.

## Files
| Patch | File |
|---|---|
| soc_dv_x18_quests | `scripts\coop_soc_dv.script`, `coop_scn_soc_dv.script`, `coop_soc_bar.script`; `configs\text\eng|rus\st_coop_soc_dv.xml` (37 SoC strings, made by `tools\gen_text.py`); `sounds\characters_voice\dialogs\eng\bar_bar_barmen_start_*.ogg` (7); copies of three level logic files: `configs\scripts\coop_l04_x18\x18_codedoor_1.ltx`, `x18_codedoor_2.ltx` (flag instead of `give_task`), `coop_l04_darkvalley\val_smart_terrain_18_walker_duty_bullet.ltx` (flag instead of `give_task`), `coop_l05_bar\space_restrictors\bar_start_sneak_into_the_x_18_lab_quest_task_space_restrictor.ltx` (inert); made by `tools\apply_logic.py` |
| darkvalley_restore | `configs\misc\tm_coop_l04_darkvalley.ltx` (new / changed task sections), `configs\scripts\coop_l04_darkvalley\space_restrictors\x18_start_get_out_of_the_lab_quest_task_space_restrictor.ltx` (raid on the documents, no `give_task`), `configs\gameplay\dialogs_coop_l04_darkvalley.xml` (Sidorovich document dialog removed) |
| quest_dialogs | `configs\gameplay\dialogs_coop_l05_bar.xml` (the three old Barkeep dialogs out, `bar_soc_barmen_start_dialog` in); `gen_quest_dialogs.py` runs `tools\apply_dialogs.py` at its end so a regeneration keeps it |
| repeatable_quests | `configs\misc\coop_hidden_tasks.ltx` (+13 ids), `configs\gameplay\character_desc_coop_l05_bar.xml` (the Barkeep starts with the SoC dialog, three dialogs unlisted), `character_desc_coop_l01_escape.xml` (Sidorovich's document dialog unlisted) |
Tools: `tools\apply_dialogs.py`, `tools\apply_logic.py` (both idempotent, edit the files other patches own), `tools\gen_text.py`, `tools\check_dv_chain.py` (static proof), `tests\mock_test.py` (Lua mock, 70 asserts), `tests\soc_dv_hooks.lua` (game test).

## Flags other levels read (checked: every read flag still has a setter, `check_dv_chain.py` part 4)
`BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO` (Rostok / Yantar restrictors, the Yantar line; now set in phrase 172 together with the transfer), `BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO` (Cordon task "Find the militaries' documents"; set in phrase 2211), `BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO` (item restrictor, set in phrase 15112), `ESC_RETURN_FROM_DV_INFO` (Cordon return zone, untouched), `VAL_RAID_START`, `X18_START_GET_OUT_OF_THE_LAB_QUEST_TASK_INFO` (helicopters of Dark Valley, still set by the raid restrictor), `BAR_START_SNEAK_INTO_THE_X_18_LAB_QUEST_TASK_INFO` (Borov autosave, now set by the tick on the job flag), `VAL_START_SNEAK_INTO_THE_X_18_LAB_1_QUEST_TASK_INFO` (lab restrictor). `BARMEN_AGR_DOC_INFO` is still set (phrase 2211) but nothing reads it any more. `ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_X18_DOCUMENTS_STOP_DIALOG_INFO` is never set now (only the hidden Sidorovich task section reads it).

## Not done / limits
- The X16 documents hand-in and the Brain Scorcher job (SoC phrases 12 / 13 / 16 / 19, three more English recordings 121, 13121, 1314), the hunter, Kruglov and the Duty / Freedom list are in `patches\bar_soc_quests`. The Yantar task `bar_start_go_to_yantar_quest_task` is now given there when the player ACCEPTS the X16 job in the dialog, no longer by this tick; after the X18 hand-in the Barkeep state is `x16offer`, not `default`. Barkeep greeting 182 (alternative of 181) is still not used.
- Serega has no dialog (SoC `val_prisoner_hello_*`) and no Bullet / captive dialogs (the stock mod has none either); the task gives its SoC text and is done by the cell switch.
- The Barkeep gives the mod's scientific outfit + key card (restrictor, as before) where SoC gives `stalker_outfit`; unchanged on purpose (needs the mod's items).
- SoC's bandit base zones are approximated by circles (see above).
- The key objective ends when Borov dies, whoever kills him; the key item itself is no longer needed (the lab entrance door was removed by `darkvalley_restore`).
- The Russian Barkeep voice ships in patch `soc_ru_voices` (see its NOTES.md).

## Offline checks done
`python patches\soc_dv_x18_quests\tests\mock_test.py` (70 PASS: the chain order, once per player, late joiner, dead / respawned player, skipped steps, Borov / Bullet / Serega dead, the states of the Barkeep, rewards, voice per language); `python -I patches\soc_dv_x18_quests\tools\check_dv_chain.py <mod source> --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` (0 problems); `tools\check_conflicts.py` (only the known overlaps); `tools\check_lua_escapes.py` (nothing new); `tools\luabal.py`; `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK.

## Game test (one listen-host run, two players, nothing human)
```
python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socdv -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\soc_dv_x18_quests\tests\soc_dv_hooks.lua -SoakSeconds 200 -ResultDir <out>\res
python tools\stalker_xrmpe\qa_verdict.py <out>\res
```
The hook fast-forwards the flags, asserts on host and client: each SoC task with SoC title / description for the local player, `coop_soc_dv.who(task)` lists every player, mod-only tasks never given, dead Borov / Serega do not block, the Barkeep states, the hand-in functions (three documents taken, 10000 paid, flag set; the documents do not go to Sidorovich: his dialog is removed), English voice file per phrase exists, silent with `rus`. Not driven: the zone positions (mock) and the real dialog window (the Bar is not online on Cordon).

## Кратко по-русски
Тёмная долина, X-18 и работа Бармена приведены к цепочке оригинальной ТЧ.
- Бармен (диалог `bar_soc_barmen_start_dialog`, оригинальные реплики RU + EN, оригинальная английская озвучка 7 реплик; русской озвучки в ТЧ нет): "Принес документы с Агропрома?" -> сдача документов, 5000 -> предлагает работу -> "Я попробую." выдаёт задание "Найти документы в подземной лаборатории": Пробраться на базу, Забрать у Борова ключ, Выбраться с базы бандитов, Найти вход в лабораторию.
- Вход в лабораторию запускает "Найти документы в X18" (найти документы, отнести Бармену). Документы сдаются БАРМЕНУ (не Сидоровичу), он платит 10000. Рейд начинается, когда найдены документы; "Выбраться из Тёмной долины" (val_come_to_trader) отменяется, если документы уже у Бармена.
- Кодовые двери: два шага "Узнать код" и "Открыть дверь с помощью кода". Добавлено "Спасти долговца" (Серёга в тюрьме бандитов). Задания SOS, гаусс-обманка, три документа, полтергейст, выход из лаборатории и "показать документы Сидоровичу" убраны.
- Каждое задание получает каждый игрок (сервер), в том числе зашедшие позже; все шаги на общих флагах, смерть Борова, Пули или Серёги цепочку не блокирует.
- Не сделано: остальной Бар (линия Долга и Свободы, охотник, Круглов, сдача документов X16 и задание Радара), диалоги Серёги, зоны базы бандитов приближены кругами.

| Было | Стало |
|---|---|
| три диалога Бармена, монологи, задание по таймеру | один диалог как в ТЧ, задание в диалоге |
| "убить Борова", 3 задания на документы, SOS, гаусс, полтергейст, "показать Сидоровичу" | 4 цели оригинального задания, одно "Найти документы", остальное убрано |
| документы показывали Сидоровичу, не отдавали | документы у Бармена, 10000 |
| кодовые двери: 1 задание, первому игроку | 2 шага, всем игрокам |
