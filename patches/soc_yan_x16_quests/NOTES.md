# Yantar and lab X-16: the quest chain of the original SoC (phase 2 of "quests must match the original")

Request (maintainer FOSTER): "the quests themselves must be remade to match the original SoC". Phase 1 (texts) is `patches\soc_task_texts`; its NOTES.md section
"Phase 2 ... X-16 and Yantar" lists the differences. This patch does the structure for Yantar (`coop_l08_yantar`) and the lab (`coop_l08_x16`). The Barkeep side of
the X16 job (job dialog, the one task `bar_start_go_to_yantar_quest_task`, the documents hand-in) is patch `bar_soc_quests`; the two patches meet on the flags below.

## The original SoC chain (Steam SoC 1.0006: tasks_yantar.xml, info_l08yantar.xml, dialogs_yantar.xml, yantar_tasks.script, brain_system_message.ltx, tasks_bar.xml)
1. Barkeep: `bar_x16_documents` ("Talk to the scientists", "Find the X16 documents", "Bring the documents to the Barkeep").
2. Sakharov (`yantar_general_ucheniy_talk_start`): the party offers its help -> `yan_find_scientist` "Take radiation measurements": 1 talk to Kruglov, 2 escort Kruglov to the
   measurement sites (ONE task), 3 bring the results to Sakharov. Kruglov sends the player ahead (`yantar_help_scientist`). Also `yan_scientist_job` "Help for the scientists"
   ("Offer help to the scientists"), done when the lab job starts.
3. Results to Sakharov: he gives the crystal flower, the prototype psi helmet (in the dialog) and starts `yan_find_vasilyev_task`: 1 search Vasiliev's corpse (his PDA names the lab),
   2 get inside the lab.
4. In the lab: `yan_find_ghost_task` "Take the documents" (get inside, take the documents from Ghost), `yan_kill_brain_task` "Turn off psi-emission" (control modules 1 to 3, then the mechanism),
   `yan_kill_brain_task_2` "Get out of the lab" (secret tunnel, Sakharov: "thanks, good prices"). Ghost's documents start `yan_provodnik_task` "Meet the Guide" (Cordon).
5. Documents to the Barkeep (`bar_x16_documents_done`), then the Brain Scorcher job (bar_soc_quests).
Not given in the normal game: `yan_find_scientist_semenov`, `yan_scientist_return_task` (Kruglov dead, replaced by the second scientist Semenov).

## Old (mod) vs new
| # | Mod before | SoC | New (this patch) |
|---|---|---|---|
| 1 | three copies of the Barkeep job (Bar, Rostok, Yantar), the Yantar one given by a Rostok zone to ONE player | `bar_x16_documents`, one task | the one task of bar_soc_quests; the Yantar copy `yan_start_go_to_yantar_quest_task` is never given (hidden). Its text and marker follow `YAN_X16_DOCUMENTS_GAIN` and the Sakharov offer flag |
| 2 | nothing | `yan_scientist_job` | `yan_soc_job_task` for every player on arrival on Yantar, done when the lab job starts (helmet flag) |
| 3 | four dialogs with invented lines (offer 7 phrases, results 7, helmet 3, "installation is disabled" 3) listed as separate topics | one tree `yantar_general_ucheniy_talk_start` | `yan_soc_saharov_dialog`: offer (SoC branch 1), offer after Kruglov was rescued (branch 10, with the suit), reminder while measuring (7), results (3), reminder before the lab (6), thanks after the lab (23), then the mod's greeting. Original wording EN + RU, original English voice for 8 lines |
| 4 | Kruglov: 5 invented lines, gives the device to the talker only | `yantar_help_scientist` | `yan_soc_kruglov_dialog`: first meeting (SoC 21 / 41), the escort talk (11, 111, 1111, 11111, 111111, 1111111: "why don't you go first"), "no time" while measuring, "how's life" afterwards. Original English voice for 2 lines |
| 5 | measurements: 3 tasks (talk, site 1, 2, 3, then "talk to Sakharov") plus 6 hidden wait / return tasks, the zones only for the host's player with the device | one task, one escort objective | `yan_start_talk_to_the_kruglov_quest_task` = SoC `yan_find_scientist`: "Talk to Kruglov" (briefing), "Escort Kruglov to the measurement site" (marker on the first undone site), "Bring the results to Sakharov". The server tick measures: a living player WITH the device in a site sphere (radius 8.2, the restrictor spheres) for 10 s, any order, for any player. The old restrictors still run beside it (same flags). If nobody holds the device any more (dead carrier) the server gives one to the first living player |
| 6 | "In the Name of Science!" (`yan_start_configuring_helmets`): Sakharov walks to his room for 50 s ("no talk"), then the task, then a restrictor creates ONE helmet | no such task: the helmet comes in the dialog | task gone, walk gone (walker copy), the restrictor only autosaves. The dialog sets the flags, the server creates a helmet for EVERY living player who has none (late joiners, respawned players) until the lab is done |
| 7 | task rewards 20000 / 30000 money (invented) | the crystal flower from Sakharov, the suit (branch 10) | the same: `af_cristall_flower` and `ecolog_outfit` for every living player, handed out once by the server; no money. The `reward_money` lines of `yan_start_talk_to_the_saharov_x16_lab_quest_task` (20000) and of `yan_start_talk_to_the_barmen_quest_task` (30000, the Barkeep's Radar job, still given by bar_soc_quests) are removed from `tm_coop_l08_yantar.ltx` (SoC pays nothing there) |
| 8 | Vasiliev does not exist, the lab opens with the helmet | `yan_find_vasilyev_task`: his corpse and PDA | a dead ecologist `yan_vasilyev` (story id = the map marker) with the PDA `yan_vasilyev_pda` next to him in the swamp where the secret tunnel comes out (graph point 0046). The PDA text is the SoC recording (item description), a PDA tip shows on pickup. Task: "Search Vasiliev's corpse" (+ Sakharov briefing), then "Get inside the lab" with the marker on the lab entrance |
| 9 | Ghost's body and documents exist (yantar_restore) but no task | `yan_find_ghost_task` | `yan_soc_ghost_task` on the lab level: "Get inside Lab X16" + Vasiliev's recording, then "Take the documents from Ghost" (marker: Ghost) |
| 10 | five tasks: find the installation, switches 1 to 4 (3 given at once, the 4th after the 3rd) | `yan_kill_brain_task` | `x16_start_find_the_installation_quest_task` = ONE task: briefing, then the lowest undone module (1, 2, 3, marker on the lever), then "Unplug the mechanism"; done when all four levers are down |
| 11 | on the tunnel flag: "get out of the lab" completed, "talk to Sakharov" (20000) and "Ask Barkeep for a job" (30000) given | `yan_kill_brain_task_2` | `x16_start_get_out_of_the_lab_task` = ONE task: "Get out via the secret tunnel" (marker: the lab exit), then "Talk to Sakharov" (marker: Sakharov), done by his thanks. "Ask Barkeep for a job" is not given here (bar_soc_quests) |
| 12 | nothing | `yan_provodnik_task` | `yan_soc_guide_task` "Meet the Guide" when Ghost's documents were taken (any level), marker on the Guide; done when a player is within 6 m of him on Cordon. The Doctor chain after it does not exist in the mod |
| 13 | every task by `give_task` (first player only), zones for the host player | | every task by the server tick (`coop_soc_yan.script`) to EVERY living player, once per level load, only while its stage is open |

## How it works
`coop_soc_yan.script` (loaded by `coop_scn_soc_yan.script`, like every `coop_scn_*`): a server tick (1 s, real time).
1. `progress()` derives the SoC infos and makes the chain monotonic (a later flag also sets every earlier one): documents in any bag -> `X16_GHOST_DOCS_TAKEN` + `YAN_X16_DOCUMENTS_GAIN`;
   PDA in any bag -> `YAN_SOC_VASILYEV_FOUND`; the party on the lab level -> `YAN_YAN_START_INFILTRATE_THE_X16_LAB_QUEST_TASK_INFO`; a lever -> the installation flag; a measurement sphere;
   the Guide. The levers themselves are never set by the script (the lab doors and the psi zone read them).
2. Every task whose stage is open on the current level is given to every living player once (`GiveTaskToClient`), so late joiners and respawned players get the open tasks; a stage closes with
   the same flag that completes its task. The description and the map marker of a task follow the flags (`descr` / `target` condlists, same syntax as patch agroprom_soc).
3. The server hands out what the dialogs promise (detector, helmet, suit, artifact): the dialogs only set flags, so nothing depends on which machine ran the dialog.
4. Dialog state (`sak_state`, `kru_state`) comes from shared flags only (same on every machine); the PDA archive line and the English voice (the talking player's machine only, language =
   `voice_language` of that player, `coop_soc_opening.voice_lang()`) are in `say_*` (written by `tools\apply_dialogs.py`).

Soft-lock rules (all server side, all in the mock test): Kruglov and Sakharov are invulnerable; the device and the helmet are re-issued; a lab level reached without the talks sets every earlier
flag (no reward is made up); Vasiliev that cannot be created (3 tries) or a lost corpse sets `YAN_SOC_VASILYEV_FOUND`; all four levers set `X16_GHOST_DOCS_TAKEN` (no documents needed to leave)
and, back on Yantar, `X16_START_GET_OUT_OF_THE_LAB_TASK_INFO` (leaving by the entrance works too); the Barkeep flag closes everything before it.

## Flags
Read by `bar_soc_quests` (the Barkeep task and dialog): `YAN_X16_DOCUMENTS_GAIN` (SET HERE and by coop_soc_barros.script: the party holds Ghost's documents), `BAR_X16_DOCUMENTS_DONE` (set by the Barkeep
dialog: documents handed in; read here, it ends the Yantar chain), `YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO` (help offered), `...KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO`
(Kruglov's escort talk, NOT his first greeting: the Rostok task "Talk to Kruglov" ends with it), `YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO` (Sakharov thanked),
`X16_GHOST_DOCS_TAKEN`. Read here from others: `ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_INFO` (Kruglov was rescued: Sakharov's branch 10), `BAR_X16_DOCUMENTS_DONE`.
Names unchanged (other files read them): the offer, Kruglov, results (`..._TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO`), helmet (`..._GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO`), the measurement and
lever flags, `YAN_YAN_START_INFILTRATE_THE_X16_LAB_QUEST_TASK_INFO`, `X16_START_FIND_THE_INSTALLATION_QUEST_TASK_INFO`, `X16_START_GET_OUT_OF_THE_LAB_TASK_INFO` (the Yantar heli scene and the
Sakharov message of yantar_restore, the dream scene of cutscenes_pkg_yantar read the lever flags).
NEW: `YAN_SOC_VASILYEV_FOUND`, `YAN_SOC_VAS_PDA`, `YAN_SOC_GUIDE_MET`, `YAN_SOC_OUTFIT_GIVEN` / `_DONE`, `YAN_SOC_REWARD_GIVEN` / `_DONE`. Not in `story_flags_table` (the engine syncs flags by name and saves them).

## Files
| Patch | File |
|---|---|
| soc_yan_x16_quests | `configs\misc\tm_coop_l08_yantar.ltx`, `tm_coop_l08_x16.ltx` (made by `tools\make_tm.py`); `scripts\coop_soc_yan.script`, `coop_scn_soc_yan.script`; `configs\text\{eng,rus}\st_coop_soc_yan.xml` (54 SoC strings, made by `tools\gen_text.py`); `sounds\characters_voice\dialogs\eng\*.ogg` (10, 0.7 MB); copies of four level logic files (made by `tools\make_logic.py`): `configs\scripts\coop_l08_yantar\yan_smart_terrain_1_walker_saharov.ltx`, `space_restrictors\yan_give_dev_psi_protection_helmet_space_restrictor.ltx`, `space_restrictors\ros_start_go_to_yantar_quest_task_space_restrictor.ltx`, `coop_l08_x16\space_restrictors\x16_start_find_the_installation_quest_task_space_restrictor.ltx` |
| quest_dialogs (edited in place) | `configs\gameplay\dialogs_coop_l08_yantar.xml`: the five level-maker dialogs out, `yan_soc_saharov_dialog` and `yan_soc_kruglov_dialog` in. `tools\apply_dialogs.py` is idempotent and `gen_quest_dialogs.py` runs it at its end, so a regeneration keeps it |
| repeatable_quests (edited in place) | `configs\gameplay\character_desc_coop_l08_yantar.xml` (Sakharov and Kruglov start with the SoC dialogs; the fetch orders `rq_sak_*` and the generic topics stay), `configs\misc\coop_hidden_tasks.ltx` (+11 retired ids) |
| yantar_restore (edited in place) | `configs\creatures\spawn_sections_coop_l08_yantar.ltx`: sections `yan_vasilyev` (corpse, profile `sim_default_ecolog_1`) and `yan_vasilyev_pda` |
Tools: `tools\make_tm.py`, `gen_text.py`, `make_logic.py`, `apply_dialogs.py` (all idempotent), `tools\check_yan_chain.py` (static proof), `tests\mock_test.py` (Lua mock, 110 checks), `tests\soc_yan_hooks.lua` (game test).

## Offline checks done
`python tests\mock_test.py` (needs lupa): 110 PASS (every player once at the right stage, late joiner, dead / respawned player, measurement zones with and without the device, the device re-issued, helmet
and artifact for everybody, Vasiliev created once / failed / existing / online alive, PDA, lab level, documents, levers, exit, Guide (online object, server entity, no object), monotonic jumps, the Barkeep
flag, exactly one Sakharov and one Kruglov state at every step, voice per language and player, PDA archive speaker). `python -I tools\check_yan_chain.py <mod source> --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`:
0 problems (every task of the tick has a section and eng + rus texts in EVERY descr / title branch, targets are story objects of the level data, retired tasks hidden, dialog functions / texts / links / reachability,
no replaced dialog left, every flag read has a setter incl. the ones bar_soc_quests reads, items and sections exist, voice files ship). `tools\check_conflicts.py` (only the known overlaps), `tools\check_lua_escapes.py`
(nothing new), `tools\luabal.py` on both scripts and the hook, `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK (headroom 21.6 MB).

## Game test (not run: offline work only; two commands, one listen-host run each, two players, nothing human)
```
python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socyan -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\soc_yan_x16_quests\tests\soc_yan_hooks.lua -SoakSeconds 450 -CompareTimeout 10 -ResultDir <out>\res
python tools\stalker_xrmpe\qa_verdict.py <out>\res
```
The hook starts on Cordon, travels to Yantar by the party vote (guide flag, `coop_map_vote.on_yes`, fallback teleport), opens the REAL dialog windows with Sakharov and Kruglov (host only), fast-forwards the flags the
dialogs set, teleports every player into the three measurement spheres, and asserts on host and client: each SoC task with its SoC title and the description that follows the flags, `coop_soc_yan.who(task)`
lists every player, helmet / artifact / device in the bags, Vasiliev's corpse and PDA exist, the old tasks are never given, the states of the two NPCs, the voice files. The lab part is the same hook with `-Cfg dest=x16`
(`-Owner socyanx -SoakSeconds 300`): the lab tasks per lever, Ghost's body, documents, the flags the Barkeep task reads, the exit task. Not driven in the game: the encounter with the zombies, the dream scene.

## Not done / limits (honest)
- Nothing here ran in the game. Not verified: that the description / target condlists (`{+A -B} id, id`) and the combined `{...}` of three flags work in this xrMPE build exactly as in the SoC engine (the same parser as the
  mod's own `condlist` lines and as patch agroprom_soc); that the real dialog windows start with the empty phrase 0 and the empty redirect phrases (the pattern of the Barkeep dialog of soc_dv_x18_quests, also not driven yet);
  the creation of the dead ecologist and the PDA by `alife():create` on Yantar (the Ghost's body of yantar_restore uses the same calls and was proven).
- Kruglov does not walk with the party (the follow scheme was reverted in yantar_restore, see its NOTES), so "Escort Kruglov to the measurement site" keeps the SoC wording while the marker shows the sites; he sends the player ahead
  with the SoC line "why don't you go first".
- `yan_find_scientist_semenov`, `yan_scientist_return_task` and the wounded scientist need NPCs the mod does not have (Semenov); Kruglov and Sakharov are invulnerable here, so those variants cannot occur: not added.
- "Meet the Guide": done when a player stands within 6 m of the Guide on Cordon (SoC: when he talks to him); the Guide has no extra lines about the Doctor and the Doctor chain (the Pripyat hotel stash) does not exist in the mod.
- Vasiliev's body is where the secret tunnel comes out, not at the SoC place (the mod's level data has no Vasiliev object); his model is a random ecologist. The SoC recording is the PDA's description and a tip.
- Voice: the English recordings of the Steam SoC exist for 8 Sakharov and 2 Kruglov lines only; the English table of that release and the recordings differ for a few lines (line 211 is much shorter on the recording), as in the original.
- Not added: the first scene of Kruglov and the professor, `yantar_attack_start` / the price policy, the bad (not calibrated) helmet, the SoC tips of the lab.
- The old measurement restrictors (host-only `on_actor_inside`) still run beside the tick (same flags, hidden tasks), they only add the autosaves.

## Кратко по-русски
Янтарь и лаборатория X-16 идут как в оригинальной ТЧ.
- Сахаров и Круглов говорят оригинальными репликами (английская озвучка оригинала для 10 реплик, в русской игре её нет). Сахаров: предложение помощи (после спасения Круглова - с костюмом), напоминания, результаты, благодарность.
- "Сделать замеры излучения" - ОДНО задание: поговорить с Кругловым, сделать три замера (игрок с прибором, 10 секунд в зоне, любой игрок), принести результаты Сахарову. Круглов за игроком не идёт (в моде это не работает), метка показывает места замеров.
- Шлем-прототип и цветок-кристалл выдаёт разговор с Сахаровым (шлем получает каждый игрок); выдуманное задание "Дождаться настройки шлемов" и деньги за задания убраны.
- "Проникнуть в лабораторию": обыскать труп Васильева на болоте (его КПК называет лабораторию), потом внутрь. В лаборатории "Взять документы" у Призрака, "Отключить пси-излучение" (три блока, потом установка) и "Выбраться из лаборатории" (секретный тоннель, потом Сахаров).
- Добавлены "Помощь ученым" и "Встретиться с проводником" (после документов Призрака; выполняется, когда игрок подходит к проводнику на Кордоне).
- Каждое задание получает каждый игрок (сервер), в том числе зашедшие позже; все шаги на общих флагах, потеря прибора, трупа или документов цепочку не блокирует.
- Не сделано: Семёнов и раненый учёный (в моде их нет), цепочка Доктора, SoC-место трупа Васильева. Проверено офлайн (проверка цепочки, мок-тест 110 проверок), в игре не запускалось.

| Было | Стало |
|---|---|
| 4 диалога Сахарова с выдуманным текстом, 5 реплик Круглова | один диалог Сахарова и один Круглова из ТЧ |
| замеры: 3 задания + 6 скрытых, зоны только для хоста | одно задание, замеры считает сервер для любого игрока |
| "Дождаться настройки шлемов", Сахаров уходит на 50 секунд, один шлем | шлем в диалоге, шлем каждому игроку |
| Васильева нет | труп и КПК Васильева, задание "Обыскать труп" |
| 5 заданий про рубильники, 3 задания на выход | "Отключить пси-излучение" и "Выбраться из лаборатории" по одному |
| задание "Помощь ученым" и "Встретиться с проводником" отсутствовали | добавлены |

Update (patch soc_doctor_chain): the Doctor chain after "Meet the Guide" now exists. The Guide has the SoC topic (esc_provodnik_start 12 to 16), which gives ESC_FIND_DOCTOR_START (this patch's tick also sets YAN_SOC_GUIDE_MET from it) and the task "Meet with Doctor"; the Doctor stands in Strelok's hiding place of the Agroprom underground and gives "Secret stash at Pripyat". The 6 m proximity completion above still works as before.

## Semenov variant
The variant with the second scientist (`yan_find_scientist_semenov`), the wounded scientist and `yan_scientist_return_task` are in patch `soc_yan_semenov` (its `tools\apply_shared.py` edits the Sakharov / Kruglov dialogs, the measurement task text and `tm_coop_l08_yantar.ltx`). Run it again after `tools\make_tm.py` or `apply_dialogs.py` regenerated those files.

