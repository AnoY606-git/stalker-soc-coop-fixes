# SoC task texts (phase 1 of "quests must match the original")

## Problem
Maintainer feedback (FOSTER, after playing Cordon and Garbage): the quest descriptions and the quests themselves must be remade to match the original.
The level maker wrote his own task titles and descriptions ("Crime and Punishment", "Total Lawlessness", "Luminaries of Science", "For Duty!", ...).
Original SoC has its own wording for the same story beats. Phase 1 (this patch) changes the TEXT only. Phase 2 (list at the end) is the structure.

## What this patch does
- Every story task of every level after Cordon whose beat exists in SoC now shows the SoC title and the SoC description, in Russian and in English.
  86 of the 126 tasks of those levels were remade; 22 have no SoC counterpart (listed below, text and logic unchanged); 18 are the level maker's generic task menu (`*_sq_*`, not story, already removed from the dialogs by `repeatable_quests`).
- The string ids of the mod are kept (`st_<task>_name`, `st_<task>_descr`), so `tm_coop_*.ltx`, scripts and dialogs are untouched. Only the text inside the id changed.
- Cordon (`coop_l01_escape`) is not touched here (the Cordon story chain is rewritten by the `cordon` patch).
- Files: 26 new files in this patch (13 levels, eng + rus); three levels already had a text file in another patch, so that copy was edited in place (one patch per file): `darkvalley_restore` (Dark Valley), `freedom_duty` (Military), `sarcophagus_count` (Sarcophagus).

## Where the SoC wording comes from
- English: the Steam SoC 1.0006 install (`gamedata.db9`/`dbb`, `config\text\eng\string_table_tasks_*.xml`, `stable_storyline_info_*.xml`), read with `tools\xdb_soc.py`.
- Russian: the SoC string table kept in the SoC add-on of the CoP port (`st_soc_strings.xml`, cp1251; the Steam install has no Russian text). Titles and objectives match the English ids one to one.
- Task structure: `config\gameplay\tasks_<level>.xml` of SoC (`game_task` = title string id + objectives; the article of type `task` attached to objective 0 is the briefing, e.g. `Bes: "The bandit scum ..."`).
- Rule used for every remade task: **title** = the SoC task title (string id = SoC task id); **description** = the SoC objective that the mod step represents; on the FIRST step of a SoC task the SoC briefing article follows (separated by two `\n`), because SoC shows it with the task. Texts are copied byte for byte (SoC uses `\n` escapes inside strings; so does this mod).
- A few SoC texts are not literal translations of each other (for example `val_come_to_trader`: Russian objective "Выбраться через южные ворота", English "Return to the trader"). Each language shows its own SoC string.

## Checks done offline
- Every changed id still exists in the eng and rus files of its level (same id order and set as before), only the intended ids differ, files decode strictly as cp1251, XML parses.
- `python tools/check_conflicts.py`: no new conflict (no other patch ships the 26 new files; the 3 edited ones were already single-owner).
- `python build.py <out>/b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`: BUDGET OK (the patch adds about 75 KB raw).
- Game test (not run here, offline job): `tests/soc_task_texts_hooks.lua`, one Russian listen-host run. See "Test plan".

## Per level: old title, new title, SoC source
Task ids are the `tm_coop_<level>.ltx` section names. "Old" = the level maker's Russian title, "New" = the SoC Russian title now shown. Descriptions are in the changed string files (`st_<task>_descr`); the SoC source column names the objective (and briefing) used for it.

### Garbage (`l02_garbage`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| gar_start_save_the_stalker_yurik_from_bandits_quest_task | Спасти Юрика | (unchanged) | NO SoC counterpart: Yurik is mod-only (hidden) |
| gar_start_talk_to_yurik_quest_task | Поговорить с Юриком | (unchanged) | NO SoC counterpart: Yurik is mod-only (hidden) |
| gar_start_talk_to_devil_quest_task | Ответить на призыв о помощи | Ответить на призыв о помощи | `gar_car_graveyard_quest` obj 0 (`gar_dialog_hellcar`) + briefing `help_for_neitrals_text` |
| gar_start_help_to_repel_the_bandits_attack_quest_task | Отбить рейд бандитов | Отбить рейд бандитов | `gar_help_dymon` obj 1 (`gar_kill_bandits`) + briefing `graveyard_raid_text` |
| gar_start_talk_to_devil_1_quest_task | Отбить рейд бандитов | Отбить рейд бандитов | `gar_help_dymon` obj 2 (`gar_hellcar_alive`) |
| gar_start_help_the_gray_to_fight_off_the_bandits_quest_task | Встретиться с Серым. | Встретиться с Серым. | `garbage_meet_stalker` obj 0 (`garbage_meet_stalker_0`) + briefing `meet_seryi_text` |
| gar_start_talk_to_gray_quest_task | Встретиться с Серым. | Встретиться с Серым. | `garbage_meet_stalker` obj 1 (`garbage_meet_stalker_1`) |
| gar_start_go_to_the_agroprom_quest_task | Получить информацию о Стрелке | Получить информацию о Стрелке | `agr_meet_krot_band` obj 0 (`agr_meet_krot_band_0`) + briefing `storyline_seriy_flash_info` |
| gar_start_help_fight_off_the_mutants_quest_task | Помочь заставе Долга | Помочь заставе Долга | `gar_kill_boars` obj 1 (`gar_kill_boars_1`) + briefing `gar_kill_boars_descr` |

### Agroprom (`l03_agroprom`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| agr_start_save_the_stalker_mole_quest_task | Спасти Крота | Спасти Крота | `agr_help_krot` obj 0 (`agr_help_krot_0`) + briefing `article_agr_krot_sos1` |
| agr_start_follow_the_stalker_mole_quest_task | Получить информацию о Стрелке | Получить информацию о Стрелке | `agr_meet_krot_band` obj 1 (`agr_meet_krot_band_1`) |
| agr_start_talk_to_the_stalker_mole_quest_task | Получить информацию о Стрелке | Получить информацию о Стрелке | `agr_meet_krot_band` obj 2 (`agr_meet_krot_band_2`) |
| agr_start_go_to_the_agroprom_underground_quest_task | Найти тайник группировки Стрелка | Найти тайник группировки Стрелка | `agroprom_find_gunslinger_cache` obj 0 (`agroprom_find_gunslinger_cache_0`) + briefing `agr_krot_secret_info` |
| agr_start_break_into_a_military_base_quest_task | Найти документы военных | Найти документы военных | `agroprom_get_military_documents` obj 1 (`agroprom_get_military_documents_1`) + briefing `agr_rats_n_soldiers_text` |
| agr_start_the_destination_is_a_bar_quest_task | Найти документы военных | Найти документы военных | `agroprom_get_military_documents` obj 2 (`agroprom_get_military_documents_2`) |

### Agroprom underground (`l03_agroprom_underground`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| agru_start_find_the_shooter_hiding_place_task | Найти тайник группировки Стрелка | Найти тайник группировки Стрелка | `agroprom_find_gunslinger_cache` obj 1 (`agroprom_find_gunslinger_cache_1`) |
| agru_start_return_to_the_surface_task | Найти тайник группировки Стрелка | Найти тайник группировки Стрелка | `agroprom_find_gunslinger_cache` obj 3 (`agroprom_find_gunslinger_cache_3`) |

### Dark Valley (`l04_darkvalley`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| val_start_sneak_into_the_x_18_lab_1_quest_task | Найти документы в Х-18 | Найти документы в Х-18 | `bar_darklab_documents2` obj 1 (`bar_darklab_documents2_1`) + briefing `bar_darklab_documents2_txt` |
| val_start_take_the_documents_to_the_barmen_quest_task | Найти документы в Х-18 | Найти документы в Х-18 | `bar_darklab_documents2` obj 2 (`bar_darklab_documents2_2`) |
| val_start_go_to_the_sos_signal_1_quest_task | Сигнал SOS | (unchanged) | NO SoC counterpart: SOS signal side story is mod-only |
| val_start_go_to_the_sos_signal_2_quest_task | Сигнал SOS | (unchanged) | NO SoC counterpart: SOS signal side story is mod-only |
| val_start_fake_gauss_1_quest_task | Новое оружие | (unchanged) | NO SoC counterpart: fake Gauss side story is mod-only |
| val_start_fake_gauss_2_quest_task | Новое оружие | (unchanged) | NO SoC counterpart: fake Gauss side story is mod-only |
| val_start_follow_the_bullet_quest_task | Отбить долговца | Отбить долговца | `val_captive_help` obj 1 (`val_captive_help_1`) + briefing `val_captive_help_txt` |
| val_start_save_the_prisoner_quest_task | Отбить долговца | Отбить долговца | `val_captive_help` obj 2 (`val_captive_help_2`) |
| val_start_get_out_via_south_gate_quest_task | Выбраться из Темной Долины | Выбраться из Темной Долины | `val_come_to_trader` obj 1 (`val_come_to_trader`) |
| val_start_show_documents_to_sidorovich_quest_task | Показать документы торговцу | (unchanged) | NO SoC counterpart: no SoC task (the documents go to the Barkeep) |

### X-18 (`l04_x18`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| x18_start_go_to_x18_doc_1_task | Найти документы в Х-18 | Найти документы в Х-18 | `bar_darklab_documents2` obj 1 (`bar_darklab_documents2_1`) |
| x18_start_go_to_x18_doc_2_task | Найти документы в Х-18 | Найти документы в Х-18 | `bar_darklab_documents2` obj 1 (`bar_darklab_documents2_1`) |
| x18_start_go_to_x18_doc_3_task | Найти документы в Х-18 | Найти документы в Х-18 | `bar_darklab_documents2` obj 1 (`bar_darklab_documents2_1`) |
| x18_start_get_out_of_the_lab_quest_task | На выход! | (unchanged) | NO SoC counterpart: no SoC task (travel step) |
| x18_start_find_the_password_x18_codedoor_1_task | Открыть кодовую дверь | Открыть кодовую дверь | `dar_codedoor_1` obj 1 (`dar_codedoor_1_1`) + briefing `pass_to_1st_door` |
| x18_start_find_the_password_x18_codedoor_2_task | Открыть дверь в командный центр | Открыть дверь в командный центр | `dar_codedoor_2` obj 1 (`dar_codedoor_2_1`) + briefing `pass_to_2nd_door` |
| x18_start_kill_the_flame_poltergeist_quest_task | "Не опять, а снова заперто!" | (unchanged) | NO SoC counterpart: no SoC task (X-18 step) |

### Bar (`l05_bar`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| bar_start_sneak_into_the_x_18_lab_quest_task | Найти документы в подземной лаборатории | Найти документы в подземной лаборатории | `bar_darklab_documents` obj 2 (`bar_darklab_documents_1`) + briefing `bar_darklab_documents_txt` |
| bar_start_go_to_yantar_quest_task | Найти документы в лаборатории X16 | Найти документы в лаборатории X16 | `bar_x16_documents` obj 0 (`x16_yantar`) + briefing `descr_bar_x16_documents` |
| bar_start_go_to_military_quest_task | Отключить Выжигатель Мозгов | Отключить Выжигатель Мозгов | `bar_radar_deactivate` obj 1 (`get_to_antennas`) |
| bar_start_find_the_family_gun_quest_task | Найти фамильное ружье | Найти фамильное ружье | `bar_hunter_rifle` obj 1 (`bar_hunter_find_rifle`) + briefing `descr_bar_hunter_rifle` |
| bar_start_the_meeting_place_cannot_be_changed_1_quest_task | Место встречи изменить нельзя | (unchanged) | NO SoC counterpart: mod-only story, no SoC task |
| bar_start_the_meeting_place_cannot_be_changed_2_quest_task | Место встречи изменить нельзя | (unchanged) | NO SoC counterpart: mod-only story, no SoC task |
| bar_start_the_meeting_place_cannot_be_changed_3_quest_task | Место встречи изменить нельзя | (unchanged) | NO SoC counterpart: mod-only story, no SoC task |
| bar_start_sq_art_1_quest_task | Заказ на "Выверт" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_art_2_quest_task | Заказ на "Грави" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_art_3_quest_task | Заказ на "Золотая рыбка" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_mutant_psevdodog_part_1_quest_task | Заказ на "Хвост Псевдособаки" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_mutant_snork_part_2_quest_task | Заказ на "Стопа Снорка" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_mutant_krovosos_part_3_quest_task | Заказ на "Щупальца Кровососа" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_killer_mutants_1_quest_task | Заказ на мутантов "NoN" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_killer_mutants_2_quest_task | Заказ на мутантов "NoN" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| bar_start_sq_killer_mutants_3_quest_task | Заказ на мутантов "NoN" | (unchanged) | generic task menu of the level maker, not SoC and not story |

### Rostok (`l06_rostok`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| ros_start_go_to_yantar_quest_task | Найти документы в лаборатории X16 | Найти документы в лаборатории X16 | `bar_x16_documents` obj 0 (`x16_yantar`) + briefing `descr_bar_x16_documents` |
| ros_start_help_kruglov_quest_task | Встретиться с Кругловым | Встретиться с Кругловым | `bar_resque_information` obj 1 (`bar_resque_scientific_information_get`) + briefing `descr_bar_resque_information` |
| ros_start_escort_kruglov_to_yantar_quest_task | Вывести Круглова на Янтарь | Вывести Круглова на Янтарь | `bar_resque_information_2` obj 1 (`bar_resque_scientific_follow`) + briefing `descr_bar_resque_information_2` |

### Military (`l07_military`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| mil_start_talk_to_the_cap_quest_task | Оказать помощь блокпосту Свободы "Барьер" | Оказать помощь блокпосту Свободы "Барьер" | `mil_blockpost_job` obj 1 (`mil_fblockpost_phase3`) + briefing `mil_blockpost_job_descr` |
| mil_start_protect_the_barrier_quest_task | Оказать помощь блокпосту Свободы "Барьер" | Оказать помощь блокпосту Свободы "Барьер" | `mil_blockpost_job` obj 2 (`mil_fblockpost_phase2`) |
| mil_start_go_to_radar_quest_task | Отключить Выжигатель Мозгов | Отключить Выжигатель Мозгов | `bar_radar_deactivate` obj 1 (`get_to_antennas`) |
| mil_start_kill_the_sniper_on_the_tower_quest_task | Убить снайпера на вышке | Убить снайпера на вышке | `mil_kill_sniper` obj 1 (`mil_kill_sniper`) |
| mil_start_talk_to_skull_about_the_assault_quest_task | Убить снайпера на вышке | Убить снайпера на вышке | `mil_kill_sniper` obj 2 (`mil_dolg_return_to_skull`) |
| mil_start_kill_lukash_quest_task | Убить Лукаша | Убить Лукаша | `mil_kill_lukash` obj 4 (`mil_kill_lukash`) |
| mil_start_kill_the_snipers_1_quest_task | Убить Лукаша | Убить Лукаша | `mil_kill_lukash` obj 1 (`mil_dolg_assault_support`) |
| mil_start_kill_the_snipers_2_quest_task | Убить Лукаша | Убить Лукаша | `mil_kill_lukash` obj 1 (`mil_dolg_assault_support`) |
| mil_start_kill_the_snipers_3_quest_task | Убить Лукаша | Убить Лукаша | `mil_kill_lukash` obj 1 (`mil_dolg_assault_support`) |
| mil_start_kill_the_snipers_4_quest_task | Убить Лукаша | Убить Лукаша | `mil_kill_lukash` obj 1 (`mil_dolg_assault_support`) |
| mil_start_report_to_max_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 1 (`mil_go_max`) + briefing `mil_lukash_job_descr` |
| mil_start_kill_skull_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_1_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_2_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_3_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_4_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_5_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_6_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_7_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_kill_the_duty_8_quest_task | Уничтожить группу Долга | Уничтожить группу Долга | `mil_lukash_job` obj 2 (`mil_kill_dolg`) |
| mil_start_max_flash_quest_task | Получить флешку у безумного снайпера | Получить флешку у безумного снайпера | `mil_mad_job` obj 1 (`mil_mad_job`) |
| mil_start_max_flash_return_quest_task | Получить флешку у безумного снайпера | Получить флешку у безумного снайпера | `mil_mad_job` obj 2 (`mil_put_flash_to_max`) |

### X-16 (`l08_x16`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| x16_start_find_the_installation_quest_task | Отключить пси-излучение | Отключить пси-излучение | `yan_kill_brain_task` obj 0 (`yan_kill_brain`) + briefing `descr_yan_kill_brain` |
| x16_start_turn_off_the_switch_1_task | Отключить пси-излучение | Отключить пси-излучение | `yan_kill_brain_task` obj 1 (`yan_switcher_off_1`) |
| x16_start_turn_off_the_switch_2_task | Отключить пси-излучение | Отключить пси-излучение | `yan_kill_brain_task` obj 2 (`yan_switcher_off_2`) |
| x16_start_turn_off_the_switch_3_task | Отключить пси-излучение | Отключить пси-излучение | `yan_kill_brain_task` obj 3 (`yan_switcher_off_3`) |
| x16_start_turn_off_the_switch_4_task | Отключить пси-излучение | Отключить пси-излучение | `yan_kill_brain_task` obj 4 (`yan_kill_brain_task`) |
| x16_start_get_out_of_the_lab_task | Выбраться из лаборатории | Выбраться из лаборатории | `yan_kill_brain_task_2` obj 0 (`yan_kill_brain_task_2`) + briefing `descr_yan_kill_brain_2` |

### Yantar (`l08_yantar`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| yan_start_go_to_yantar_quest_task | Найти документы в лаборатории X16 | Найти документы в лаборатории X16 | `bar_x16_documents` obj 0 (`x16_yantar`) + briefing `descr_bar_x16_documents` |
| yan_start_talk_to_the_kruglov_quest_task | Сделать замеры излучения | Сделать замеры излучения | `yan_find_scientist` obj 1 (`yan_talk_to_kruglov`) + briefing `descr_yan_find_scientist` |
| yan_start_take_measurements_1_quest_task | Сделать замеры излучения | Сделать замеры излучения | `yan_find_scientist` obj 2 (`yan_psi_zone_find`) |
| yan_start_take_measurements_2_quest_task | Сделать замеры излучения | Сделать замеры излучения | `yan_find_scientist` obj 2 (`yan_psi_zone_find`) |
| yan_start_take_measurements_3_quest_task | Сделать замеры излучения | Сделать замеры излучения | `yan_find_scientist` obj 2 (`yan_psi_zone_find`) |
| yan_start_talk_to_the_saharov_quest_task | Сделать замеры излучения | Сделать замеры излучения | `yan_find_scientist` obj 3 (`yan_return_to_bunker`) |
| yan_start_configuring_helmets_quest_task | Во имя науки! | (unchanged) | NO SoC counterpart: helmet prototypes: no SoC task |
| yan_start_infiltrate_the_x16_lab_quest_task | Проникнуть в лабораторию | Проникнуть в лабораторию | `yan_find_vasilyev_task` obj 2 (`yan_find_vasilyev_task`) |
| yan_start_talk_to_the_saharov_x16_lab_quest_task | Выбраться из лаборатории | Выбраться из лаборатории | `yan_kill_brain_task_2` obj 2 (`yan_scientist_return`) |
| yan_start_talk_to_the_barmen_quest_task | Работа на бармена | Работа на бармена | `bar_barman_job_3` obj 1 (`bar_barman_job_text`) |
| yan_start_wait_for_the_measurements_to_finish_1_quest_task | "Замеры начались!" | (unchanged) | NO SoC counterpart: hidden step, no SoC task |
| yan_start_return_to_the_measurement_location_1_quest_task | "Замеры прерваны!" | (unchanged) | NO SoC counterpart: hidden step, no SoC task |
| yan_start_wait_for_the_measurements_to_finish_2_quest_task | "Замеры начались!" | (unchanged) | NO SoC counterpart: hidden step, no SoC task |
| yan_start_return_to_the_measurement_location_2_quest_task | "Замеры прерваны!" | (unchanged) | NO SoC counterpart: hidden step, no SoC task |
| yan_start_wait_for_the_measurements_to_finish_3_quest_task | "Замеры начались!" | (unchanged) | NO SoC counterpart: hidden step, no SoC task |
| yan_start_return_to_the_measurement_location_3_quest_task | "Замеры прерваны!" | (unchanged) | NO SoC counterpart: hidden step, no SoC task |
| yan_start_sq_art_1_quest_task | Заказ на "Кристалл" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_art_2_quest_task | Заказ на "Огненный шар" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_art_3_quest_task | Заказ на "Глаз" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_mutant_snork_part_1_quest_task | Заказ на "Стопа Снорка" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_mutant_krovosos_part_2_quest_task | Заказ на "Щупальца Кровососа" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_mutant_chimera_part_3_quest_task | Заказ на "Коготь Химеры" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_killer_mutants_1_quest_task | Заказ на мутантов "На болоте около Бункера ученых" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_killer_mutants_2_quest_task | Заказ на мутантов "Справа от Бункера ученых" | (unchanged) | generic task menu of the level maker, not SoC and not story |
| yan_start_sq_killer_mutants_3_quest_task | Заказ на мутантов "Около Упавшего вертолёта" | (unchanged) | generic task menu of the level maker, not SoC and not story |

### Radar (`l09_radar`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| rad_start_go_to_radar_quest_task | Отключить Выжигатель Мозгов | Отключить Выжигатель Мозгов | `bar_radar_deactivate` obj 2 (`find_and_deactivate_radar`) |

### X-10 (`l09_x10`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| x10_start_turn_off_the_radar_quest_task | Отключить Выжигатель Мозгов | Отключить Выжигатель Мозгов | `bar_radar_deactivate` obj 3 (`deactivate_radar_now`) |
| x10_start_leave_the_bunker_and_go_to_pripyat_quest_task | Найти вход в Саркофаг на ЧАЭС | Найти вход в Саркофаг на ЧАЭС | `rad_get_to_aes` obj 0 (`rad_get_to_aes`) + briefing `rad_get_to_aes_desc` |

### Pripyat (`l10_pripyat`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| pri_start_go_to_cnpp_quest_task | Найти вход в Саркофаг на ЧАЭС | Найти вход в Саркофаг на ЧАЭС | `rad_get_to_aes` obj 3 (`pripyat_task_objective_2`) |
| pri_start_meet_a_group_of_stalkers_quest_task | Встретиться с группой сталкеров | Встретиться с группой сталкеров | `pripyat_task_1` obj 0 (`pripyat_task_title`) |
| pri_start_help_the_stalkers_get_to_the_underground_parking_quest_task | Встретиться с группой сталкеров | Встретиться с группой сталкеров | `pripyat_task_1` obj 1 (`pripyat_task_objective_1`) |

### Control Monolith (`l11_control_monolith`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| con_start_sneak_into_the_control_room_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 0 (`sar_monolith_destroy_0`) + briefing `sar_command_center_text` |
| con_start_destroy_the_monolith_installation_1_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 1 (`sar_monolith_destroy_1`) |
| con_start_destroy_the_monolith_installation_2_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 1 (`sar_monolith_destroy_1`) |
| con_start_destroy_the_monolith_installation_3_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 1 (`sar_monolith_destroy_1`) |
| con_start_destroy_the_monolith_installation_4_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 1 (`sar_monolith_destroy_1`) |
| con_start_destroy_the_monolith_installation_5_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 1 (`sar_monolith_destroy_1`) |
| con_start_destroy_the_monolith_installation_6_quest_task | Загадка Монолита | Загадка Монолита | `sar_monolith_destroy` obj 1 (`sar_monolith_destroy_1`) |
| con_start_talk_to_the_representative_awareness_quest_task | Загадка Зоны | Загадка Зоны | `sar_warlab` obj 1 (`sar_perception_1`) |
| con_start_kill_all_representatives_of_awareness_quest_task | Пора со всем покончить! | (unchanged) | NO SoC counterpart: no SoC task (SoC only talks to them) |

### Sarcophagus (`l11_sarcofag`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| sar_start_get_to_the_monolith_quest_task | Исполнитель желаний | Исполнитель желаний | `sar_monolith` obj 0 (`sar_monolith_0`) + briefing `sar_monolith_call_text` |
| sar_start_kill_the_monolith_preacher_quest_task | Пора со всем покончить! | (unchanged) | NO SoC counterpart: Preacher is not in SoC |
| sar_start_search_the_preacher_body_and_retrieve_the_decoder_quest_task | Пора со всем покончить! | (unchanged) | NO SoC counterpart: decoder from the Preacher is not in SoC |
| sar_start_open_the_door_to_monolith_management_quest_task | Секретная лаборатория | Секретная лаборатория | `sar_secret_lab` obj 2 (`sar_secret_lab_2`) |

### Stancia (NPP) (`l11_stancia_1`)
| task id | old rus title | new rus title | SoC source |
|---|---|---|---|
| aes_1_start_go_to_sarcofag_quest_task | Найти вход в Саркофаг на ЧАЭС | Найти вход в Саркофаг на ЧАЭС | `rad_get_to_aes` obj 4 (`rad_get_to_aes_1`) |

## Mod tasks without a SoC counterpart (text left as it was, logic untouched)
- gar_start_save_the_stalker_yurik_from_bandits_quest_task (Garbage): Yurik is mod-only (hidden)
- gar_start_talk_to_yurik_quest_task (Garbage): Yurik is mod-only (hidden)
- val_start_go_to_the_sos_signal_1_quest_task (Dark Valley): SOS signal side story is mod-only
- val_start_go_to_the_sos_signal_2_quest_task (Dark Valley): SOS signal side story is mod-only
- val_start_fake_gauss_1_quest_task (Dark Valley): fake Gauss side story is mod-only
- val_start_fake_gauss_2_quest_task (Dark Valley): fake Gauss side story is mod-only
- val_start_show_documents_to_sidorovich_quest_task (Dark Valley): no SoC task (the documents go to the Barkeep)
- x18_start_get_out_of_the_lab_quest_task (X-18): no SoC task (travel step)
- x18_start_kill_the_flame_poltergeist_quest_task (X-18): no SoC task (X-18 step)
- bar_start_the_meeting_place_cannot_be_changed_1_quest_task (Bar): mod-only story, no SoC task
- bar_start_the_meeting_place_cannot_be_changed_2_quest_task (Bar): mod-only story, no SoC task
- bar_start_the_meeting_place_cannot_be_changed_3_quest_task (Bar): mod-only story, no SoC task
- yan_start_configuring_helmets_quest_task (Yantar): helmet prototypes: no SoC task
- yan_start_wait_for_the_measurements_to_finish_1_quest_task (Yantar): hidden step, no SoC task
- yan_start_return_to_the_measurement_location_1_quest_task (Yantar): hidden step, no SoC task
- yan_start_wait_for_the_measurements_to_finish_2_quest_task (Yantar): hidden step, no SoC task
- yan_start_return_to_the_measurement_location_2_quest_task (Yantar): hidden step, no SoC task
- yan_start_wait_for_the_measurements_to_finish_3_quest_task (Yantar): hidden step, no SoC task
- yan_start_return_to_the_measurement_location_3_quest_task (Yantar): hidden step, no SoC task
- con_start_kill_all_representatives_of_awareness_quest_task (Control Monolith): no SoC task (SoC only talks to them)
- sar_start_kill_the_monolith_preacher_quest_task (Sarcophagus): Preacher is not in SoC
- sar_start_search_the_preacher_body_and_retrieve_the_decoder_quest_task (Sarcophagus): decoder from the Preacher is not in SoC
- All `*_sq_*` tasks (Bar, Yantar): the level maker's generic menu. SoC's own jobs are the generated ones of `repeatable_quests`.
- Hidden for good (`coop_hidden_tasks.ltx`) and not shown to players anyway: Yurik x2, the Yantar wait/return measurement steps.

## SoC tasks that the mod has no step for (after Cordon)
- Garbage: nothing missing at task level (see structure list).
- Agroprom: `agr_help_stalkers` (variant of the Mole fight), `agroprom_find_stalker_phantom`, `agr_find_ghost` (Ghost chain toward Yantar).
- Dark Valley: `val_prisoner_help` (free the Duty member from the bandit prison).
- Bar: `bar_barman_job_1`, `bar_barman_job_2` ("Work for Barkeep"), the Duty line `bar_dolg_community_quest`, `bar_dolg_base_rules`, `bar_dolg_test_quest`, `bar_crazy_veterans_quest`, `bar_dolg_svoboda_ambush_quest`, `bar_dolg_svoboda_leader_kill_quest`.
- Military: `mil_courier_job` (the snitch), `mil_freedom_rg6_task` (Bulldog 6, Voronin).
- Yantar: `yan_scientist_job`, `yan_find_scientist_semenov`, `yan_scientist_return_task`, `yan_find_ghost_task`, `yan_provodnik_task`.
- Pripyat / NPP: `cit_doctor_task` (the hotel stash with the decoder), `aes_military_task` (Operation Monolith). Dead City tasks (`cit_documents`, `cit_killers_base`, ...) belong to a level the mod has not.

## Phase 2: structure differences (plan, NOT changed in this patch)
Differences between the mod's task chain (`tm_coop_*.ltx`, restrictors, walker logic) and the SoC chain (`tasks_*.xml`, `info_*.xml`). Order of work: first the lines marked "giver", then missing steps, then mod-only steps.

Legend: "giver" = who/what hands out the task (SoC: dialog or info portion; mod: trigger zone, walker logic or dialog), "missing" = SoC objective/task the mod has no step for, "extra" = mod step with no SoC objective. SoC facts come from `tasks_*.xml` and the `<task>` entries of `info_*.xml`; mod facts from `tm_coop_*.ltx` chains and the restrictor / walker files that call `give_task`.

### Garbage
**DONE in `patches/garbage_soc_quests` (see its NOTES.md); the list below is the plan that was worked off.**
- giver: `garbage_meet_stalker` ("Meet with Seriy") is given in SoC by Fox on Cordon (info `garbage_find_stalker`, task text "Fox: Seriy is sitting in the hangar"). The mod starts it only on Garbage, from `gar_smart_terrain_7_walker_gray.ltx`, after a mod-only fight. Plan: give it from Fox's dialog on Cordon (coordinate with the Cordon chain) and from arrival on Garbage as a fallback.
- extra: "help the Gray fight off the bandits" (`gar_start_help_the_gray_to_fight_off_the_bandits`) has no SoC objective; SoC goes straight to "Learn something of Strelok from Seriy". Yurik (2 tasks, hidden) is mod-only.
- giver / order: Bes. SoC gives `gar_car_graveyard_quest` automatically on arrival (info `gar_start_quest`), then `gar_help_dymon` when the player offers help (info `gar_hellcar_help`); the mod gives the first one from `gar_smart_terrain_2_walker_devil.ltx` and chains the other two. Order matches; only check that the second task is given by the dialog answer and not by the walker.
- missing: `gar_kill_boars` has 3 objectives (header, kill the boars at the nest `gar_boars_nest`, "Talk with the Duty commander" `gar_dolg_blockpost` to get through to the Bar). The mod has only the kill step (zone `gar_duty_rush_space_restrictor.ltx`); no return-to-commander step and no reward step.
- giver: `agr_meet_krot_band` objective 0 is given by Seriy at the end of his dialog in SoC (the mod keeps it as the Garbage task "go to Agroprom": fine, but it must be given by Seriy's dialog and not by a trigger).

### Agroprom and Agroprom underground
**DONE in `patchesgroprom_soc` (see its NOTES.md); the list below is the plan that was worked off.**
- order: SoC `agr_meet_krot_band` is "meet Mole's group" then "get info from Mole"; the fight is the separate task `agr_help_krot` (kill the soldiers, save Mole) or `agr_help_stalkers`. The mod does fight, then "follow Mole", then talk. extra: "follow Mole" (`agr_start_follow_the_stalker_mole`) has no SoC objective (in SoC Mole stays at the factory and the stash route comes from his talk).
- missing: `agr_help_stalkers` (the variant where the group is attacked and Mole is not the target), `agroprom_find_stalker_phantom` and `agr_find_ghost` (the Ghost chain that leads to Yantar), `agroprom_find_gunslinger_cache` objective 2 "Find information about Strelok in the stash" (take the flash drive), `agroprom_get_military_documents` objective 0 header.
- giver: SoC gives `agroprom_get_military_documents` from the Trader on Cordon (info `escape_need_agroprom_documents`, "Work for the trader"), before the player is on Agroprom. The mod gives it from `agr_start_return_to_the_surface_task_end_space_restrictor.ltx` after leaving the underground. Plan: keep the Cordon-side task (the `cordon` patch already gives it) and let the Agroprom side only advance objective 1 / 2.

### Dark Valley and X-18
DONE (phase 2, 2026-10-21): see `patches\soc_dv_x18_quests\NOTES.md` (Barkeep job dialog, four-objective job, code doors, documents to the Barkeep, Serega, mod-only steps hidden). The list below is the state before that work.
- missing: `val_prisoner_help` (free the Duty member Serega from the bandit prison); `bar_darklab_documents` objectives "Sneak into the base", "Get out of the bandit base", "Find the entrance to the lab" (the mod only has the Borov key step, given on the Bar); `dar_codedoor_1/2` objective 2 "Open the door using the code" (the mod has one step per door).
- extra: SOS signal x2 and "fake Gauss" x2 (`val_smart_terrain_16_*` restrictors), "show documents to Sidorovich" (SoC hands the X-18 documents to the Barkeep: `bar_darklab_documents2` objective 2, and `val_come_to_trader` is the way out), the poltergeist step and "get out of the lab" (X-18).
- giver: `val_captive_help` comes from Bullet (`val_smart_terrain_18_walker_duty_bullet.ltx`), same as SoC. `bar_darklab_documents2` starts in SoC on entering the lab (info `dar_run_quest`); the mod starts it when the player arrives in Dark Valley (check the trigger).
- order: SoC `val_come_to_trader` ("Get out of the Dark Valley") fails when the documents are done (`bar_darklab_document_done`); the mod gives it from the X-18 exit zone after the documents task. Compare after the documents handover.

### Bar
DONE (phase 2, 2026-10-21): see `patches\bar_soc_quests\NOTES.md` (Barkeep X16 / Scorcher jobs as dialog steps, one `bar_x16_documents` task, hunter return step, Kruglov talk steps, mod-only steps hidden; the Duty / Freedom line is listed there, none of it can be done without new map content). The list below is the state before that work.
- giver: the three Barkeep jobs (`bar_barman_job_1/2/3`, "Work for Barkeep") are dialog steps in SoC and each starts the next real task (`bar_darklab_documents`, `bar_x16_documents`, `bar_radar_deactivate`). The mod starts those by trigger zones (`bar_start_sneak_into_the_x_18_lab_quest_task_space_restrictor.ltx`, `bar_start_go_to_military_quest_task_space_restrictor.ltx`, ...). Plan: put them behind the Barkeep dialog (`quest_dialogs` gating already exists).
- missing: `bar_x16_documents` objectives "Find the X16 documents" / "Bring the documents to the Barkeep" (the mod has only the "talk to the scientists" start and a separate Yantar line); `bar_hunter_rifle` objective 2 "Return the rifle to the hunter at the Bar" (the mod task is a leaf); `bar_resque_information` objective 2 "Talk to professor Kruglov".
- missing (whole Duty / Freedom line, none of it exists in the mod): `bar_dolg_community_quest`, `bar_dolg_base_rules`, `bar_dolg_test_quest`, `bar_crazy_veterans_quest`, `bar_dolg_svoboda_ambush_quest`, `bar_dolg_svoboda_leader_kill_quest`, `mil_freedom_rg6_task`.
- extra: "The meeting place cannot be changed" x3 (mod-only story with Garbage meeting-place zones).
- order: `bar_start_go_to_military` sends the player to the Military level with the title "Time to head to the Center of the Zone". In SoC the Barkeep sends the player to the Radar (Brain Scorcher) only after the X-16 documents; Military is optional side content.

### Rostok
DONE (phase 2, 2026-10-21): see `patches\bar_soc_quests\NOTES.md` (the two "Talk to Kruglov" steps, the duplicate `ros_start_go_to_yantar` is hidden). The list below is the state before that work.
- missing: `bar_resque_information` objective 2 "Talk to professor Kruglov" and `bar_resque_information_2` objective 2 "Talk to Kruglov" (the mod goes straight from rescue to escort and from escort to Yantar). giver: `ros_smart_terrain_3_kruglov_help_space_restrictor.ltx` gives the rescue; SoC starts it with info `bar_rescue_research_start`.
- extra: `ros_start_go_to_yantar` repeats the Bar task `bar_start_go_to_yantar` (SoC has one task `bar_x16_documents`).

### Military
DONE (phase 2, 2026-10-21) except the snitch and the Bulldog 6 order (no NPCs in the mod): see `patches\soc_mil_quests\NOTES.md`. The list below is the state before that work.
- missing: `mil_courier_job` (Lukash: the snitch Pavlik, 5 objectives), `mil_freedom_rg6_task`; `mil_lukash_job` objective 3 "Return to Lukash"; `mil_kill_lukash` objective 5 "Return to the Duty farmstead and receive my fee"; `mil_blockpost_job` objective 3 "Talk to Barrier outpost commander" (reward step).
- extra / counts: SoC has 3 snipers (`Mil_Sniper1..3`), the mod has 4 sniper tasks; SoC has one "Destroy the Duty squad" objective, the mod has "kill Skull" plus 8 "kill the Duty" tasks; `mil_start_go_to_radar` has no SoC objective on this level.
- giver: check the zones `mil_cap_pda_1_space_restrictor.ltx` and `mil_start_report_to_max_quest_task_space_restrictor.ltx` against SoC (Lukash and the Freedom outpost give `mil_blockpost_job`, Skull gives the Duty line, Max the Freedom line, infos `mil_lukash_blockpost`, `mil_sniper_get_job`, `mil_lukash_get_job`).

### X-16 and Yantar
DONE (phase 2, 2026-10-21): see `patches\soc_yan_x16_quests\NOTES.md` (Sakharov / Kruglov dialogs of SoC, measurements as one task, helmet by dialog, Vasiliev, Ghost, the lab tasks, "Help for the scientists", "Meet the Guide"). The list below is the state before that work.
- missing: `yan_scientist_job` (offer help to the scientists), `yan_find_scientist_semenov` (the variant with the second scientist), `yan_scientist_return_task`, `yan_find_vasilyev_task` objective 1 "Search Vasiliev's corpse", `yan_find_ghost_task` ("Take the documents": Ghost, Lab X16 entrance), `yan_provodnik_task` ("Meet the Guide", starts the Doctor chain after the lab), `yan_kill_brain_task_2` objective 1 "Get out via the secret tunnel".
- order: SoC goes measurements, results to Sakharov, Vasiliev's corpse (lab location), Ghost's documents, the lab, the switches, exit, Sakharov, Barkeep. The mod goes measurements, results, "configuring helmets", lab, switches, exit. The Vasiliev and Ghost steps are skipped.
- extra: measurements are 3 separate tasks with hidden wait / return steps (`yan_start_take_measurements_1..3_space_restrictor.ltx`); SoC has one task with one escort objective. `yan_start_configuring_helmets` has no SoC objective.
- giver: `yan_start_configuring_helmets` is given by `yan_smart_terrain_1_walker_saharov.ltx`; SoC gives the lab task through Sakharov's dialog after the Vasiliev info.

### Radar, X-10, Pripyat, Stancia
DONE in patch `soc_aes_quests` (see its NOTES.md): the differences below are resolved or listed there as not done.
- missing: `cit_doctor_task` ("Secret stash at Pripyat": hotel, room with the stash, decoder; it gives `sar_secret_lab`), `aes_military_task` ("Operation Monolith", the assault with the military squads), `pripyat_task_1` objective 2 "Find the path to the Chernobyl NPP" (the mod covers it in `pri_start_go_to_cnpp`).
- order: in SoC `rad_get_to_aes` is ONE task given on the Radar (info `rad_task_aes`) with objectives that run through Pripyat to the Sarcophagus; the mod splits it into `x10_start_leave_the_bunker...`, `pri_start_go_to_cnpp`, `aes_1_start_go_to_sarcofag`. Fine as long as the titles stay the same (they now do).
- extra: none; the Pripyat meet / follow stalkers steps appear in SoC both inside `rad_get_to_aes` and as `pripyat_task_1`.

### Control Monolith and Sarcophagus
DONE in patch `soc_aes_quests` (see its NOTES.md): the differences below are resolved or listed there as not done.
- missing: `sar_monolith` objectives "Sneak in to the sarcophagus" and "Find the Wish Granter"; `sar_secret_lab` objectives "Enter the secret bunker", "Find the hidden door", "Find out what is behind the door".
- extra: the Preacher (kill him, search his body for the decoder; not in SoC, where the decoder comes from the Pripyat hotel stash `cit_doctor_task`), "kill all representatives of O-Consciousness" (SoC only talks to them: `sar_warlab`), and 6 "destroy the Monolith installation" tasks where SoC has one objective "Solve the Monolith's secret".
- order: SoC: Wish Granter (`sar_monolith`), decoder from Pripyat, secret lab door (`sar_secret_lab`), control room (`sar_monolith_destroy`), meeting (`sar_warlab`). The mod reaches the door through the Preacher.

## Test plan (one Russian listen-host run)
1. Build a stage: `python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage`.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\qa_lang.ps1 -Lang rus -Owner tasktxt -Expect 1 -RunCoopArgs "-Map coop_l01_escape -Owner tasktxt -Mode listen -Clients 1 -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\soc_task_texts\tests\soc_task_texts_hooks.lua -SoakSeconds 30 -CompareTimeout 5 -ResultDir <out>\res"`
3. The hook (`--@qa_lib`) calls `game.translate_string(id)` for every changed id (142 ids) and asserts the SoC text (rus run: Russian table; `-Cfg lang=eng` run without `qa_lang`: English table); whitespace is collapsed on both sides because the engine turns `\n` into a line break. Verdict: `python tools\stalker_xrmpe\qa_verdict.py <out>\res`.
4. Cordon is enough for the strings (the string table is global). Not covered: seeing the text in the PDA of each level (the same ids that the tasks already used).

## Кратко по-русски
Фаза 1 задачи "квесты должны соответствовать оригиналу": названия и описания сюжетных заданий всех уровней после Кордона заменены на оригинальные тексты SoC (русский и английский). Номера строк (`st_<задание>_name` / `_descr`) прежние, логика не тронута.
- Правило: название = название задания SoC; описание = цель SoC, которую изображает шаг мода; на первом шаге задания следом идёт вводный текст SoC (реплика заказчика).
- Источники: английский из установки SoC (Steam), русский из строк SoC в аддоне порта CoP; структура из `tasks_<уровень>.xml` SoC.
- Переделано 86 заданий из 126; без аналога в SoC: 22 (список выше, текст и логика прежние); `*_sq_*` это общее меню автора уровня, не сюжет.
- Файлы: новый патч `soc_task_texts` (13 уровней, 26 файлов); для Тёмной долины, Военных и Саркофага правлены копии в `darkvalley_restore`, `freedom_duty`, `sarcophagus_count` (один файл = один патч).
- Фаза 2 (структура: кто даёт задание, лишние и недостающие шаги, порядок) описана списком по уровням выше, в этом патче не менялась.
- Кордон не тронут (его цепочку переписывает патч `cordon`).
