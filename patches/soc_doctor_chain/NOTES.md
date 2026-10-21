# The Guide and the Doctor: the chain after Ghost's documents (phase 2 of "quests must match the original SoC")

Request (maintainer FOSTER): "the quests themselves must be remade to match the original SoC". `soc_yan_x16_quests` ends with the task "Meet the Guide" and says the Doctor chain does not exist in the mod;
`soc_aes_quests` places the decoder stash in the Pripyat hotel but hands the stash task out when the party reaches Pripyat, with the Doctor's text and no Doctor. This patch adds the missing middle:
the Guide's talk, the Doctor and the task he gives. Added size: 0.69 MB in the db (15 files, 0.7 MB of the original English voice), no model, no texture.

## The original SoC chain (Steam SoC 1.0006: dialogs_escape.xml, dialogs_deadcity.xml, info_l01escape.xml, info_l08deadcity.xml, tasks_yantar.xml, tasks_escape.xml, tasks_deadcity.xml, `agr_knockdown.ltx`, `cit_doctor.ltx`, `xr_effects.script`, level.spawn of l03u_agr_underground)
1. Ghost's documents (Yantar) start `yan_provodnik_task` "Meet the Guide" ("Talk to Guide"); the Guide (`esc_provodnik`) stands at the Cordon camp by the bridge.
2. Guide dialog `esc_provodnik_start` (branch 12 to 16): "Guide, I need to see Doctor." / "How do you know about Doctor?" / "Ghost sent me. Help me get in touch with Doctor. It's urgent." / "Doctor is in Strelok's hiding place. If you are who you say you are, you probably know where it is." / "Thank you."
   The last NPC phrase gives `esc_find_doctor_start`: it completes "Meet the Guide", starts the task `doctor_meet` "Meet with Doctor" (objective "Meet with Doctor at Strelok's hiding place", marker `agr_doctor_spot`) and adds the Guide's PDA note.
3. Strelok's hiding place is the room of the stash in the Agroprom underground. A restrictor there (`rostok_dist_to_actor_le(8)`, `agr_knockdown.ltx`) fires once `esc_find_doctor_start` is set: explosion, tinnitus, earthquake camera, black screen, the Doctor (`cit_doctor`, story id 350,
   waits at -69.76 -6.87 -70.50) is spawned, the player is teleported to the Dead City jail (`kat_teleport_to_dark_city_position`), `esc_find_doctor_done` is set, 85 s later `cit_jail_doctor_pryp_task` is given.
4. Dead City, the jail cell: `cit_doctor_hello_dialog` ("Strelok! Where the hell have you been???"), then `cit_doctor_main_dialog`: the Doctor recognises Strelok, the player does not remember him, Ghost is dead ("I found his body in Yantar"), the Doctor
   gives the key (`cit_doctors_key`) and the map of the stash at Pripyat and says Strelok kept saying something was wrong with the Monolith. Info `cit_jail_doctor_pryp_task` starts `cit_doctor_task` "Secret stash at Pripyat" (hotel, room, look the stash over),
   `cit_doctor_meet_conclusion_info` adds the diary entry "Meeting with the Doctor" ("I found out that I am the Shooter ..."). The Doctor's second dialog `cit_doctor_escape_dialog` (his things, the sewer, who holds us, the map of the city, who is in charge) leads into the Dead City quests
   (compromising documents, the Merc base map, kill the leader, Vasily Petrovich) and the jail escape.
5. The stash holds the decoder: `sar_secret_lab` (patch soc_aes_quests).

## Old (mod) vs new
| # | Mod before | SoC | New (this patch) |
|---|---|---|---|
| 1 | the Guide only offered the level trips; "Meet the Guide" was completed by standing within 6 m of him | Guide dialog 12 to 16, `esc_find_doctor_start` | topic `soc_doc_guide_dialog` on the Cordon Guide (original lines EN + RU, no recording exists for the Guide), offered once Ghost's documents are taken (`X16_GHOST_DOCS_TAKEN`) and until he has spoken; its last NPC phrase gives `ESC_FIND_DOCTOR_START`. The Yantar tick's proximity completion stays; this patch also sets `YAN_SOC_GUIDE_MET` from the dialog flag |
| 2 | nothing | `doctor_meet` "Meet with Doctor" + the Guide's PDA note | `soc_doc_meet_task` (title and objective 2 of `doctor_meet`, the Doctor's note as briefing) given by the server tick to EVERY player (late joiners and respawned players too, once per level load) while the Doctor is not met; the marker is the Doctor once he exists. The PDA note shows once per player (scene `soc_doc_guide_pda`) |
| 3 | no Doctor | `cit_doctor` waits at -69.76 -6.87 -70.50 of the Agroprom underground, then the Dead City cell | the Doctor (profile `soc_cit_doctor`, model `actors\stalker_mp\stalker_doctor`, the same skin the SoC Doctor has and the mod already ships) is created ONCE by `alife():create` at that SoC spot (AI node 3563, game vertex 689, recomputed by `check_doctor_chain.py --verify-spot`) when the party is on the underground and the Guide has spoken. Story id `soc_cit_doctor`, invulnerable, ignores combat, looks at the player (his own logic file). Pattern of the Cordon technician (registry check, no duplicate, logic started by script when the engine did not) |
| 4 | no knock-out | `agr_knockdown`: knock-out, teleport to the jail, `esc_find_doctor_done` | no knock-out and no teleport (no destination). A player within 8 m of the SoC knock-out zone (or 10 m of the Doctor) sets `ESC_FIND_DOCTOR_DONE`, which ends "Meet with Doctor" |
| 5 | no talk | `cit_doctor_hello_dialog`, `cit_doctor_main_dialog` 0 to 4 | NPC greeting `soc_doc_hello_dialog` (first meeting / after the talk, from the shared flag) and the topic `soc_doc_main_dialog` (phrases 0, 1, 11, 2, 21, 3, 31, 4 with the SoC wording EN + RU). The original English recordings of 5 of his lines play (per-player voice language, `coop_soc_opening.voice_lang()`, the mechanism of patch cutscenes_pkg_opening; Russian: silent, the Russian SoC has none). PDA archive lines like the other SoC dialogs. The last phrase gives `CIT_JAIL_DOCTOR_PRYP_TASK` and `CIT_DOCTOR_MEET_CONCLUSION_INFO` |
| 6 | the stash task only on Pripyat | `cit_doctor_task` "Secret stash at Pripyat" given by the Doctor | `soc_doc_stash_task` (title `cit_doctor_task`, objective 0 "Find the secret stash of the Shooter at Pripyat" + the Doctor's briefing) for every player on every level before Pripyat while the decoder is not taken. It completes with `PRI_MONOLITH_DECODER_GOT` or `PRI_ACTOR_IN_HOTEL` (where the first stash step of soc_aes_quests ends) and fails when the party leaves for CNPP-1, like those steps. On Pripyat soc_aes_quests gives its own three steps as before |
| 7 | no diary | `cit_doctor_meet_conclusion` | the diary text "Meeting with the Doctor" shows once per player (scene `soc_doc_conclusion`) |

## How it works
`coop_soc_doctor.script` (loaded by `coop_scn_soc_doctor.script`, like every `coop_scn_*`): a server tick (1 s, real time), the pattern of `coop_soc_yan.script`.
1. `progress()`: the party on Pripyat or later, or the decoder taken, sets `SOC_DOC_CLOSED` (the chain is over: tasks and the Guide topic are gone, no Doctor is created; this is also what keeps the free play after the ending quiet, the flags stay set, nothing replays);
   `ESC_FIND_DOCTOR_DONE` comes from the positions; the chain is monotonic (a later flag sets the earlier ones: a party that is past the Doctor never waits for him).
2. Every open task is given to every living player once per level load (`GiveTaskToClient`), only while its stage is open.
3. The Doctor is created on the underground when the Guide has spoken (once, story registry, a stale entry is dropped, a registry that lost him re-registers the existing one, create failures stop after 3 tries). If the Doctor is ever dead, the talk flags are given so the stash task still follows (no reward is made up).
4. The dialogs only set flags; the states of the Doctor's greeting and the preconditions of the topics are computed from shared flags, so they are the same on every machine.
Nothing in `soc_aes_quests`, `soc_yan_x16_quests` or `freeplay` reads a flag of this chain: skip the Doctor, kill him, never talk to the Guide, and every other chain behaves as before.

## Flags
SoC infos (names as in SoC, upper case): `ESC_FIND_DOCTOR_START` (Guide dialog), `ESC_FIND_DOCTOR_DONE` (the party came to the hiding place), `CIT_JAIL_DOCTOR_PRYP_TASK` (Doctor dialog), `CIT_DOCTOR_MEET_CONCLUSION_INFO` (Doctor dialog). New: `SOC_DOC_CLOSED`.
Read from others: `X16_GHOST_DOCS_TAKEN` (soc_yan_x16_quests / yantar_restore), `PRI_MONOLITH_DECODER_GOT`, `PRI_ACTOR_IN_HOTEL`, `PRI_START_GO_TO_CNPP_QUEST_TASK_INFO`, `SOC_AES_CNPP_ARRIVED` (soc_aes_quests). Set for others: `YAN_SOC_GUIDE_MET` (soc_yan_x16_quests).
Not in `story_flags_table`: the engine syncs flags by name and saves them (same as the other SoC chains).

## Files
| Where | File |
|---|---|
| soc_doctor_chain (new) | `scripts\coop_soc_doctor.script`, `coop_scn_soc_doctor.script`; `configs\gameplay\dialogs_coop_soc_doctor.xml` (3 dialogs, made by `tools\make_xml.py`), `npc_profile_soc_doctor.xml`, `character_desc_coop_soc_doctor.xml`; `configs\creatures\spawn_sections_coop_soc_doctor.ltx`; `configs\scripts\coop_l03_agroprom_underground\soc_cit_doctor.ltx` (his logic); `configs\misc\tm_coop_soc_doctor.ltx` (2 tasks); `configs\text\{eng,rus}\st_coop_soc_doctor.xml` (25 SoC strings, made by `tools\gen_text.py`); `sounds\characters_voice\dialogs\eng\cit_doctor_*.ogg` (5 files, SoC `scenario\cit`, copied unchanged) |
| edited by `tools\apply_shared.py` (NOT run on the repo yet) | `repeatable_quests\...\configs\system.ltx` (the three file lists and the include of the spawn section file), `...\misc\task_manager.ltx` (include of `tm_coop_soc_doctor.ltx`), `...\gameplay\character_desc_coop_l01_escape.xml` (the Guide gets `soc_doc_guide_dialog`), `installer\changes_1.4.en|ru.txt` and `changes_1.4.1.en|ru.txt` (one line each), `NOTES.md` of soc_yan_x16_quests and soc_aes_quests (one update line each) |
Tools: `tools\apply_shared.py` (idempotent, `--check`), `make_xml.py`, `gen_text.py`, `check_doctor_chain.py` (static proof), `tests\mock_test.py` (Lua mock, 57 checks), `tests\soc_doctor_hooks.lua` (game test).

## After the zip: the coordinator's steps
```
python tools\apply_shared.py            (in patches\soc_doctor_chain; idempotent; --check lists what is still missing)
python -I tools\check_conflicts.py soc_levels weapon_upgrades npc_attachments arrival_facing inventory_carry
python -I patches\soc_doctor_chain\tools\check_doctor_chain.py <mod source dir> --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing
python -I build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
```
Without `apply_shared.py` the patch is inert (its files are never read: no dialog is registered, nobody can reach the Doctor), so a build made before it runs is safe, just without this chain.

## Planned changes line (also in `apply_shared.py`, tag `@soc_doctor_chain`, no em dashes)
EN: The Guide and the Doctor of the original SoC. Once you have taken Ghost's documents, the Cordon Guide has a new topic ("Guide, I need to see Doctor.", the original lines): the Doctor waits in Strelok's hiding place, "Meeting with Doctor" goes to every player and the Guide's PDA note shows. In the Agroprom underground the Doctor stands in that hiding place (his original spot), recognises Strelok, hears that Ghost is dead and hands over the task "Secret stash at Pripyat" (diary "Meeting with the Doctor"); the original English voice plays for his lines. The task leads to the decoder in the Pripyat hotel (see the entry above). Nothing blocks: a dead Doctor or a party that goes straight to Pripyat just skips the chain. Not in the mod: the Dead City (in the original you are knocked out in the underground and wake up in its jail), so the Doctor's jail talks and the Dead City quests are missing.

RU: Проводник и Доктор из оригинальной ТЧ. Когда вы взяли документы Призрака, у Проводника на Кордоне появляется новая тема ("Проводник, мне нужно встретиться с Доктором.", оригинальные реплики): Доктор ждёт в тайнике Стрелка, задание "Встретиться с Доктором" получает каждый игрок, в КПК приходит записка Проводника. В подземельях Агропрома Доктор стоит в этом тайнике (на своём месте из оригинала), узнаёт Стрелка, слышит, что Призрак мёртв, и даёт задание "Тайник на Припяти" (дневник "Встреча с Доктором"); его реплики озвучены оригинальной английской озвучкой. Задание ведёт к декодеру в гостинице Припяти (см. запись выше). Ничто не блокируется: погибший Доктор или отряд, ушедший сразу в Припять, просто пропускают цепочку. В моде нет Мёртвого города (в оригинале вас оглушают в подземелье и вы приходите в себя в его тюрьме), поэтому разговоров Доктора в тюрьме и заданий Мёртвого города нет.

## What is still impossible, and why
- **The Dead City** (`l09_deadcity` in SoC) does not exist in the mod: no level, no all.spawn part, no AI mesh. So there is no knock-out and teleport (the destination is missing), no jail cell, no escape through the sewer, no Merc base and no Dead City quests (compromising documents, the Merc base map, kill the leader Dushman, Vasily Petrovich, the `quest_cit_reward` trade). The Doctor's second dialog `cit_doctor_escape_dialog` (his things, the sewer, "who captured us", the city map, "who is in charge") only makes sense in that cell and is not added; of `cit_doctor_main_dialog` the two lines "where are we / we are in the Dead City, in the Merc camp" (41, 5, 6) are left out for the same reason.
- **Strelok's past beyond the talk**: SoC tells it only through the Doctor's talk and the diary entry, both are in. The rest of the Dead City story (the Mercs hunting Strelok) lives on the missing level.
- **The knock-out effects** (explosion, tinnitus, earthquake camera, black screen) were not added alone: without the wake-up in the jail they would only be an unexplained interruption.
- **The key** `cit_doctors_key`: no such item in the mod, and the Pripyat hotel door is unlocked in the mod (SoC locks it until the Doctor gives the key, see the soc_aes_quests notes). The Doctor's line "take it" stays, as in SoC where the player gets the key in the same moment, but no item is created.
- **A recording for the Guide** and **Russian voice**: the Steam SoC has no recording for the Guide's lines and the Russian SoC data has none for these dialogs, so those lines are silent (text only).
- Not proven in the game (offline task, nothing was launched): that the engine opens the NPC-first start dialog of an NPC made by `alife():create` (the technician does the same), the Doctor's idle animation `ward_noweap` with `target = actor`, and the task marker on a story id. The hook below drives all of them.

## Offline checks done (scratch copy of the repo with `apply_shared.py` applied)
- `python patches\soc_doctor_chain\tests\mock_test.py` (needs lupa): 57 PASS (nothing without the chain, the Guide topic states, both tasks to every player once, late joiner, dead player, the Doctor created once at the SoC spot with node 3563 / game vertex 689, registry lost / stale entry, create failure stops after 3 tries, no player online,
  dead Doctor does not block, party past the Doctor closes the chain, free play with every flag set, client does nothing, install / reinstall, voice per language, PDA archive speaker).
- `python -I tools\check_doctor_chain.py <mod source> --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --verify-spot <coop.addon>`: 0 problems (shared edits present, 18 dialog phrases reachable with eng + rus texts and existing functions, profile and specific character, spawn section / story id / logic file, the model `actors\stalker_mp\stalker_doctor` is in the mod, both tasks have eng + rus texts and resolve their marker and flags, voice files, scene texts; node 3563 / game vertex 689 recomputed from level.ai and the effective all.spawn).
- `python -I tools\luabal.py` on both scripts and the hook; `python -I tools\check_lua_escapes.py` (nothing new: 3 old lines of other patches); `patches\freeplay\tests\freeplay_mock_test.py` (50 PASS), `soc_yan_x16_quests\tests\mock_test.py`, `soc_aes_quests\tests\mock_test.py` (83 PASS): unchanged.
- `tools\check_conflicts.py soc_levels weapon_upgrades npc_attachments arrival_facing`: only the known overlaps, none from this patch. `tools\lint_configs.py` on the stage: nothing new from this patch.
- `python -I build.py <scratch>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK: this patch adds 0.69 MB (db 52,075,514 -> 52,795,472 bytes in the scratch tree). It ships no .ogf, so no `models\capture` file can be missing.

## Game test (not run: offline work only; two players on a listen host, nothing human)
```
python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socdoc -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\soc_doctor_chain\tests\soc_doctor_hooks.lua -SoakSeconds 300 -CompareTimeout 10 -ResultDir <dir>
python <games>\tools\stalker_xrmpe\qa_verdict.py <dir>
```
(`<games>` is the folder that holds `stalker-soc-coop-fixes` and `tools`; `apply_shared.py` must have been run before the build, or the hook finds no Guide topic.) Lines in `qa_events.log` start with `SOCDOC`.

## По-русски (кратко)
Добавлена цепочка Проводник, Доктор, "Тайник на Припяти" из оригинальной ТЧ, которой не хватало между заданием "Встретиться с проводником" (soc_yan_x16_quests) и тайником с декодером в гостинице Припяти (soc_aes_quests).
- У Проводника на Кордоне новая тема "Проводник, мне нужно встретиться с Доктором." (оригинальные реплики) после документов Призрака; она даёт задание "Встретиться с Доктором" всем игрокам и записку Проводника в КПК.
- В подземельях Агропрома в тайнике Стрелка, на месте из оригинала, стоит Доктор (создаётся один раз, неуязвим). Разговор: оригинальные реплики, английская озвучка из ТЧ у 5 фраз; в конце задание "Тайник на Припяти" всем игрокам и запись дневника "Встреча с Доктором".
- Ничто не блокируется: убитый Доктор или отряд, ушедший сразу в Припять, пропускают цепочку; Припять (soc_aes_quests) и свободная игра после финала работают как раньше.
- Невозможно: Мёртвого города нет в моде, поэтому нет оглушения и телепорта в тюрьму, тюремных разговоров Доктора (побег, база наёмников, карта, Душман), заданий Мёртвого города и ключа Доктора. Для Проводника нет записей озвучки.
- Размер: +0,69 МБ. Правки чужих файлов (system.ltx, task_manager.ltx, профиль Проводника, строки changes, NOTES) делает `tools\apply_shared.py` после сборки zip.

## Review notes (independent check)
- SoC fidelity checked against the Steam SoC files: the Guide lines (esc_provodnik_start 12 to 16), the Doctor's greeting and talk, the task and diary strings are SoC strings (eng from the Steam tables, rus from the SoC add-on); the Doctor's position in all.spawn is -69.7555 -6.8732 -70.4957 (the spawner condition there is agr_doc_wakeup, the knock-out); the SoC Doctor visual `actors\izgoy\izgoy` uses the texture `act\act_stalker_doctor`, the same skin as the mod's `stalker_mp\stalker_doctor`; the 5 voice files are byte-size identical to the Steam recordings.
- Fixed in review: a party that reaches Pripyat (chain closed) with Ghost's documents but without having met the Guide now also closes the Yantar task "Meet the Guide" (before it stayed open for ever); the change lines are also added to `changes_1.4.1.en|ru.txt` (both lists carry the quest chain lines); mock test now 58 checks.
- Known and accepted: on Pripyat the task "Secret stash at Pripyat" of the Doctor and the first step of soc_aes_quests (same title) are both listed until the hotel is reached.
