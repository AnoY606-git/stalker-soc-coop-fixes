# soc_yan_semenov: Yantar, the second scientist of the original SoC (Semenov, the wounded scientist, the return task)

Part of "the quests must match the original SoC" (maintainer FOSTER). `patches\soc_yan_x16_quests` (see its NOTES, "Not given in the normal game") left out `yan_find_scientist_semenov`,
the wounded scientist and `yan_scientist_return_task` because the mod had no NPC for them. This patch adds the NPCs, their SoC logic and dialogs, and hooks them into the Sakharov chain of
`soc_yan_x16_quests` WITHOUT changing that patch's scripts.

Planned changes line (EN, in `installer\changes_1.4.en.txt` and `changes_1.4.1.en.txt` by `tools\apply_shared.py`):
"- @soc_yan_semenov,soc_yan_x16_quests,quest_dialogs,repeatable_quests,yantar_restore: Yantar: the second scientist of the original. When the Wild Territory professor was not rescued, Sakharov now sends you with the assistant Semenov (a new NPC next to the bunker, the original talk) instead of Kruglov. After the three measurements Semenov lies wounded at the last site and can be talked to; if the zombies kill him, Sakharov asks you to come back ("Talk to Sakharov" with the PDA message) and gives the prototype anyway, as in the original. The wounded scientist and his talk exist only in this Semenov variant."

Planned changes line (RU, `changes_1.4.ru.txt` / `changes_1.4.1.ru.txt`): the same sentence in Russian, see `tools\apply_shared.py` (LINE_RU).

## The original SoC (Steam SoC 1.0006: dialogs_yantar.xml, tasks_yantar.xml, info_l08yantar.xml, gulag_yantar.ltx, level.spawn / level.game of l08_yantar, the logic of `yan_ecolog_spam_space_restrictor`)
- Two scientists stand at the Yantar bunker: Kruglov (`yan_scientist_help`, story id 900) and the research assistant Semenov (`yantar_semenov`, story id 905, spawn (32.78, -11.72, -276.72)). The
  restrictor `yan_ecolog_spam_space_restrictor` sets `bar_heli_scene_professor_die` + `bar_rescue_research_fail` on Yantar when `bar_rescue_research_done` is not set: the professor of the Wild
  Territory is dead. Then Sakharov's offer is branch 21113 / 211131 / 211132 ("Talk to Semenov and get going") and gives `yan_find_scientist_semenov_start`; with the professor alive it is 21112 (Kruglov).
- Task `yan_find_scientist_semenov` has the same title as `yan_find_scientist` ("Take radiation measurements"): "Talk to Semenov", "Escort Semenov to the measurement site" (marker on him,
  story id `yan_semenov_help`), "Bring the results to Sakharov". Semenov uses the dialog `yantar_help_scientist` (branch 5: 51 - 515; before the offer branch 6 "no time").
- At the third site the scientist is wounded by the psi-emission (path `yan_scientist_wounded_walk`, `wounded@yan_scientist`, `help_start_dialog = yantar_wounded_scientist`): the talk sets
  `yan_scientist_return_to_bunker`, he walks home.
- If he dies (`death@scientist` sets `yan_scientist_die`) the restrictor sends, 4 s later and while the lab job has not started, the PDA tip `general_ecolog_tip_1` (after his talk:
  `general_ecolog_tip_2`) and, without the talk, gives `yan_scientist_return_task` ("Talk to Sakharov"). Sakharov branch 5 (51 ... 51114) gives the prototype anyway and starts the Vasiliev search.

## What was added
| What | How |
|---|---|
| Professor dead = Semenov variant | `YAN_SOC_PROFESSOR_DIE` (SoC `bar_heli_scene_professor_die`) is set by the server tick when the party is on Yantar and `ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_INFO` (rescued, used by `bar_soc_quests` and `soc_yan_x16_quests`) is not set, exactly the condition of the SoC restrictor. The Sakharov offer 21112 (Kruglov) needs a living professor (`st_prof_alive`), 21113 (Semenov) a dead one. Rescued party: nothing changes. NOTE: a party that never rescued Kruglov (before: Kruglov variant) now gets the Semenov variant, like in SoC |
| Semenov at the bunker | `scripts\coop_soc_yan_semenov.script`: the server tick creates ONE NPC with `alife():create("yan_soc_semenov", ...)` at the SoC spawn point (AI node, nearest game vertex of the level, same code as the Cordon technician that was proven in game), story id registry so a loaded game finds him, full duplicate scan only once, `ensure_logic()` starts `configs\scripts\coop_l08_yantar\yan_soc_semenov.ltx` by script if the engine did not read `custom_data`. He stands and looks at Sakharov's place, invulnerable. Character `yan_soc_semenov` (SoC `yan_Semenov`: name "Assistant Semenov", bio, rank, supplies, the mod's ecolog model `stalker_ecolog_1`, portrait `ui_inGame2_neutral_nauchniy`) |
| Semenov's dialog | `yan_soc_semenov_dialog` = SoC `yantar_help_scientist` for him: before the offer 61 "I'm sorry, I have no time", the escort talk 5 - 51 - 511 - 512 - 513 (sets the preparation flag, the device is handed out by the tick of `coop_soc_yan`) - 514 - 515, busy 101, after the results 71. SoC EN + RU texts. Voice: 514 plays the recording of Kruglov's 111111 (same words), EN and RU |
| Kruglov while the professor is dead | his dialog states yield (`st_k_*` wrappers) and he only says SoC branch 6 / 61 "no time" |
| Sakharov | offer 21113 / 211131 / 211132 (sets the offer flag and `YAN_FIND_SCIENTIST_SEMENOV_START`), branch 5 "Semenov died" (51 ... 51114: the flags `REPORTED` + `HELMET` in the FIRST phrase, the helmet comes from the tick, no artifact as in SoC), the results branch 3 yields to it. EN voice of 51, 5111, 511111, 511111111 (0.46 MB, Steam SoC) and RU voice (0.65 MB, the Russian SoC sounds.zip of FOSTER) |
| The measurement task | the same mod task (`yan_start_talk_to_the_kruglov_quest_task`, SoC `yan_find_scientist`): its text and marker now follow `YAN_FIND_SCIENTIST_SEMENOV_START`: "Talk to Semenov" (marker Semenov), "Escort Semenov to the measurement site" (the open site / the wounded scientist), "Bring the results to Sakharov". It fails when the scientist dies before the talk (SoC `yantar_tasks.yan_scientist_task_fail`). No second task id: SoC's two tasks have one title and the one task serves both variants |
| The wounded scientist | after the third measurement (Semenov variant, results not delivered) the tick removes the bunker Semenov ("he is away with the player") and creates `yan_soc_semenov_wounded` (story id `yan_semenov_help`, the SoC marker id) at the first point of the SoC path `yan_scientist_wounded_walk` (171.98, -7.69, -99.49), 6.7 m from the third site. Logic `yan_soc_semenov_wounded.ltx`: `wounded@yan_soc_semenov` (SoC `hp_state = 102|...`, always wounded, `enable_talk`, `help_start_dialog = yan_soc_wounded_dialog`), mortal, `on_death` sets `YAN_SCIENTIST_DIE`. Dialog `yan_soc_wounded_dialog` = SoC `yantar_wounded_scientist` (11 / 111 sets `YAN_SCIENTIST_RETURN_TO_BUNKER`, 211, 31). 20 s after the talk (or when the results are delivered) he "goes home": the tick removes him and puts the bunker Semenov back. Optional: the results go to Sakharov without him |
| The return task | `yan_soc_return_task` (SoC `yan_scientist_return_task`, title and briefing from SoC): 4 s after his death, while the lab job has not started, the PDA tip (scene `yan_semenov_tip_1`, SoC `general_ecolog_tip_1`; after his talk tip 2 only) and the task for EVERY living player, late joiners and respawned players too; done by the prototype (helmet flag) |

The bunker Semenov is also watched: if he dies (he is invulnerable, but a logic that did not start or a stray hit could kill him) the tick sets `YAN_SCIENTIST_DIE` after Sakharov's offer (branch 5 gives the prototype anyway, no waiting for a corpse) or, before the offer, removes the corpse and creates a new one.

All flags are shared story flags (saved, synced). No soft-lock: the wounded scientist is optional, his death only changes Sakharov's branch, a lost entity is re-created / re-registered, a failed create is retried after 5 s, nothing waits for an NPC.

## One scientist at the bunker (SoC: Semenov only when the professor is dead, otherwise Kruglov only)
- Kruglov variant (professor rescued): the tick creates no Semenov (an older save that has him gets him released once). Kruglov is untouched.
- Semenov variant: once Semenov stands there (or the scientist died / the trip started), the tick releases the mod's own Yantar Kruglov (`yan_smart_terrain_1_ecolog_kruglov`, story id 900) through his squad `yan_smart_terrain_1_ecolog_kruglov_squad` (`sim_board:remove_squad`, the call the mod's Rostok Kruglov logic uses), else the entity itself; never both in one frame. Flag `YAN_SOC_KRUGLOV_GONE` (saved) makes it once, saves that already have both are fixed on the next Yantar visit.
- Nothing needs Kruglov in this variant: Semenov's dialog sets the preparation flag, the task text and marker use `yan_soc_semenov` / `yan_semenov_help`, the Kruglov dialogs only said "no time". Not run in the game.

## Name, talk and door (report from v1.4.5: "stands by the door, does nothing, no dialogs, generic name, door blocked again")
- Spot: the SoC point (32.78, -11.72, -276.72) is 1.6 m from the door `yan_door_trader_2_1` (31.2, -11.6, -277.5) and 0.7 m from Kruglov's look point; a standing NPC in the swing of the (always open) door blocks it. Semenov now stands on the
  middle of a segment of Kruglov's own path `yan_smart_terrain_1_walker_kruglov_3_1_walk`: (36.95, -11.72, -274.93), 2.8 m from Kruglov, 6.3 m from that door, 9.8 m from the locked one.
  A game that was saved with the old position keeps him there (the registry finds the old entity).
- Name and talk: both come from the specific character `yan_soc_semenov`. The two spawn sections said `spec_rank = veteran` while the character has rank 2071 (master); every named NPC of the mod (Sakharov, Kruglov, the whole Bar) has the
  matching spec_rank. The likely result was a generic scientist with the same model (green suit), another name and another start dialog (no talk). Both sections are `master` now (file of `yantar_restore`; `apply_shared.py` text updated).
  The server logs `SOCSEM IDENTITY id=.. name=.. profile=.. pos=..` once per NPC so a live run shows what the engine gave him (name must be "Assistant Semenov", the SoC string `yan_semenov_name`, Russian "Помощник Семёнов").
- Before Sakharov's offer Semenov only says the SoC phrase 61 "I'm sorry, I have no time for this right now." (SoC branch 6, same as the original); the escort talk opens after Sakharov's offer 21113.
- Visual: SoC `actors\ecolog\stalker_ecolog` is a green scientist suit; the mod ships `stalker_ecolog_1` (same suit), no new mesh.

## What is still impossible or not done, and why
- **Semenov walking with the player and walking home through the bunker doors** (SoC `help_walk_*`, `return_walk`, `door_*_walk`): NPC following was not proven in the mod (`yantar_restore` item 3: Kruglov did not move), so the measurements stay with the device in the three spheres; the hand-over (removed here, back at the bunker) replaces the walk home.
- **The Wild Territory heli scene that kills the professor**: the mod has no such scene (Kruglov of Rostok is invulnerable), so "professor dead" is derived the way the SoC restrictor does it (not rescued when on Yantar).
- **The wounded scientist for the Kruglov variant** (rescued party): Kruglov's logic and dialog belong to `soc_yan_x16_quests` / the level maker; he stays invulnerable at the bunker. Only the Semenov variant has the trip end with the wounded man.
- **SoC branches 8 / 9** (the scientist died AFTER being healed, the player takes the device `kruglov_flash` from the body): the mod's device is a generated item handed out by the tick, there is no `kruglov_flash` to take.
- **The scene voice lines** `yantar_kruglov_radiation_quest_*` (remarks of the scientist during the trip, Russian originals exist in sounds.zip): they are sound themes of the SoC remark logic which the mod does not have; the wounded scientist uses the stock heavy-wounded voice.
- **A second NPC model** for Semenov: SoC `stalker_ecolog` is the mod's `stalker_ecolog_1` (shared with the mod's Kruglov), so both look alike; no model is shipped (size).
- **English voice** for the lines that have no SoC recording (21113, 211131, the dialogs of Semenov and the wounded scientist except 514): SoC itself has none; they are silent.
- Not run in the game (offline work only).

## Shared files: `tools\apply_shared.py` (idempotent, run it AFTER the release zip / before `build.py`, never on a tree that is being packed)
`python -I patches\soc_yan_semenov\tools\apply_shared.py [<repo root>]` changes files other patches ship (a second run changes nothing):
1. `quest_dialogs\...\dialogs_coop_l08_yantar.xml`: the Sakharov and Kruglov edits above and the two new dialogs.
2. `repeatable_quests\...\character_desc_coop_l08_yantar.xml`: the specific character; `cordon_technician` and `freedom_duty` `...\npc_profile_addon.xml`: the profile (the build takes the last copy, both are kept in step).
3. `yantar_restore\...\spawn_sections_coop_l08_yantar.ltx`: the sections `yan_soc_semenov` and `yan_soc_semenov_wounded` (profile, story id, `custom_data` = the logic file).
4. `soc_yan_x16_quests\...\tm_coop_l08_yantar.ltx`: the text / marker branches and the fail line of the measurement task, the new task `yan_soc_return_task`.
5. `installer\changes_1.4.en|ru.txt` and `changes_1.4.1.en|ru.txt`: one line after the Yantar line; `soc_yan_x16_quests\NOTES.md`: a pointer; `soc_yan_x16_quests\tools\check_yan_chain.py`: it also resolves the functions and flags of this patch's script.
It must be run again after `quest_dialogs\tools\gen_quest_dialogs.py`, `soc_yan_x16_quests\tools\apply_dialogs.py` / `make_tm.py` regenerated those files (they would drop the edits). The patch's own files (script, logic, texts, voice) need no step.

## Files of this patch
`gamedata\scripts\coop_soc_yan_semenov.script` (tick, NPCs, dialog states, voice, say_*), `coop_scn_soc_yan_semenov.script` (loader + the two PDA tips), `gamedata\configs\scripts\coop_l08_yantar\yan_soc_semenov.ltx`,
`yan_soc_semenov_wounded.ltx`, `gamedata\configs\text\eng|rus\st_coop_soc_yan_semenov.xml` (34 SoC strings, `tools\gen_text.py`), `gamedata\sounds\characters_voice\dialogs\eng\*.ogg` (4) and `...\dialogs\*.ogg` (4).
**Size added: 1,143,261 bytes (1.09 MB raw, ogg does not compress) plus a few KB of text in the shared files.** No model, texture or .ogf is shipped, so no `models\capture` ltx can be missing.
Tools: `tools\gen_text.py`, `tools\apply_shared.py`, `tools\check_semenov_chain.py`; tests: `tests\mock_test.py`, `tests\soc_yan_semenov_hooks.lua`.

## Offline checks done (on a scratch copy of the repo: patches copied, `apply_shared.py` applied twice (second run: nothing to change))
- `python tests\mock_test.py` (needs lupa; runs the REAL `coop_soc_yan.script` and `coop_soc_yan_semenov.script`): 72 PASS (variant by rescue flag, Semenov created once at the SoC spot and
  registered, Kruglov / Semenov / wounded dialog states, three measurements -> wounded at the SoC spot and the bunker one removed, no duplicates, talk -> home after 20 s, results without the talk, death -> flags,
  tip 1 / 2, the return task for both players, late joiner, dead and respawned player, once per player, no task after the helmet, other levels, no player, failing create + retry, logic started by script after 2 idle
  ticks, EN / RU voice paths and files, speaker table, install / re-install).
- `python -I patches\soc_yan_semenov\tools\check_semenov_chain.py <scratch repo>`: ALL PASS (dialog graph, functions, texts EN + RU, flag setters, task branches, spawn sections, profile, logic sections and the patrol path of the mod level, model in the mod, positions against the SoC dump / `level.game`, voice files, size, no model).
- `python -I patches\soc_yan_x16_quests\tools\check_yan_chain.py <mod source> --skip=...` after the apply: 0 problems; `python patches\soc_yan_x16_quests\tests\mock_test.py`: ALL PASS.
- `tools\luabal.py` on both scripts and the hook: OK; `lupa` parse of the hook: OK; `tools\check_lua_escapes.py`: nothing new (3 old lines); `tools\check_conflicts.py`: only the known overlaps (no new file is shared); `tools\lint_configs.py`: nothing for this patch (55 old weapon lines).
- `python -I build.py <scratch>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`: BUDGET OK (db 54.5 MB, headroom 13.6 MB with this patch and the other patches of the moment), `verify_db` 0 problems.

## Game test (written, NOT run: offline work only)
Two listen-host runs, two players each, nothing human (`tests\soc_yan_semenov_hooks.lua`; `<stage>` = `build.py ... --stage=<out>\stage` of a tree with `apply_shared.py` applied):
```
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socsem -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\soc_yan_semenov\tests\soc_yan_semenov_hooks.lua -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir>
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socsemd -Cfg die=1 -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\soc_yan_semenov\tests\soc_yan_semenov_hooks.lua -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir2>
python tools\stalker_xrmpe\qa_verdict.py <dir>
```
Run A: Cordon start, party-vote travel to Yantar; asserts the professor-is-dead flag, Semenov online / alive / at the SoC spot with an active scheme, the real dialog windows with Semenov and Sakharov, the task text per flag, the device, three measurements, the wounded scientist (online, near the SoC spot, `xr_wounded.is_wounded`, talk enabled), the real wounded dialog, the stand-up, the walk home (wounded gone, bunker Semenov back).
Run B (`die=1`): the same up to the wounded scientist, then `L.kill` on him: `YAN_SCIENTIST_DIE`, the tip flag, the return task in every player's PDA (title and briefing), Sakharov's branch 5 dialog, helmets for every player.
First things to look at if something fails: the server log lines `SOCSEM created ... / logic ... started by script / released`, `xr_wounded` (a wounded NPC that does not lie down means the `wounded` section was not applied: check `active_scheme` and `db.storage[id].wounded`).

## Кратко (RU)
Добавлен Семёнов (второй учёный ТЧ), раненый учёный и задание "Поговорить с Сахаровым" (`yan_scientist_return_task`). Профессор "мёртв" так же, как в ТЧ: на Янтарь пришли, а профессор Дикой
территории не спасён (флаг `ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_INFO` не стоит). Тогда Сахаров предлагает идти с Семёновым (оригинальные реплики 21113 / 211131 / 211132), а у Круглова
остаётся только "Мне сейчас некогда". Семёнов создаётся скриптом у бункера в точке ТЧ (32.78, -11.72, -276.72), его диалог из `yantar_help_scientist` (ветка 5). После трёх замеров он лежит раненый
у третьего места (путь `yan_scientist_wounded_walk`), диалог `yantar_wounded_scientist`; через 20 секунд после разговора "уходит домой" (сервер убирает его и возвращает Семёнова к бункеру). Если зомби
убьют раненого, через 4 секунды приходит сообщение КПК и задание "Поговорить с Сахаровым", а ветка 5 Сахарова (51 ... 51114, оригинальная озвучка EN и RU) всё равно выдаёт прототип. Общие файлы других
патчей правит `tools\apply_shared.py` (идемпотентный, запускать после сборки архива). Добавлено 1.09 МБ (озвучка). Не сделано: настоящая ходьба Семёнова за игроком и домой (в моде не работает), сцена
с вертолётом на Дикой территории, раненый учёный для варианта с Кругловым, ветки 8 / 9 (устройство `kruglov_flash`). Проверено офлайн (мок-тест, проверка цепочки, сборка), в игре не запускалось.
