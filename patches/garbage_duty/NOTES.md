# garbage_duty: the Duty checkpoint on the Garbage as in the original SoC (code-only, UNTESTED in game)

Report (FOSTER, v1.4): the checkpoint soldiers do not look like the original, the boar attack ends without the commander, and the gate to the Bar is
open. Reference: SoC 1.0006 (Steam archives, `dialogs_garbage.xml`, `character_desc_garbage.xml`, `gulag_garbage.ltx`, `xr_effects.gar_boars_counter`,
`news_manager`), the Russian texts of the CoP port add-on, the Russian voice already in the mod.

## What SoC does
* Smart terrain `gar_dolg_blokpost`: 8 Duty (class `gar_dolg_blokpost`), skins `stalker_do_balon_8` x2, `stalker_do_antigas` x2, `stalker_do_balon_80` x3, and the
  commander (`gar_dolg_blokpost_commander`, name Prapor, skin `stalker_do_balon_4`).
* The road to the Bar is closed: without the story info `gar_free_pass` the guards stop you ("Halt, stalker. You can't go any further!", dialog
  `gar_dolg_blokpost`). The pass comes from the military case (Agroprom documents), from paying (500 in SoC), or from the boar favor.
* Boar attack (`gar_boars_counter`, boars `mob_death` + `killed_by_actor`): after it the commander speaks by PDA tip with voice: `gar_actor_looser`
  (`duty_after_rush_bad`: "you are rubbish, no thanks"), `gar_actor_normal`, `gar_actor_winner` (`duty_after_rush_good`: "payment enough for your pass").

## Changes
| What | How |
|---|---|
| Skins | New class `gar_dolg_blokpost` (3 specific characters, skins balon_8 / antigas / balon_80; spawn section `gar_dolg_blokpost`, profile line in `freedom_duty\...\npc_profile_addon.xml`). The SoC meshes are the ones of the CoP port add-on (`meshes\actors\dolg\*`, 4 files, 1.9 MB) plus `act_soldier_head1.dds`; all other textures already exist in the mod. Squads `gar_smart_terrain_9_duty_1..3_squad` and the Prapor squad use the class (`squad_descr_coop_l02_garbage.ltx`, owned by `garbage_gray`); the walker jobs (`gar_smart_terrain_9_walker_duty.ltx` here, `gar_smart_terrain_9_animpoint_duty.ltx` in `campfires`) take `check_npc_name(gar_dolg_blokpost)`. Head count unchanged (11 + Prapor). |
| Commander | `gar_smart_terrain_8_duty_prapor`: skin `stalker_do_balon_4`, start dialog `gar_duty_pass_start_dialog` (new in `dialogs_coop_l02_garbage.xml`). Phrase ids and texts are the SoC `gar_dolg_blokpost` ones (the mod already had 6 of them as `..._duty_prapor_start_dialog_0` / `..._the_destination_is_a_bar_0..4`; the SoC texts are in `st_garbage_duty.xml` eng + rus). |
| Gate | The Garbage exit to the Bar (`gar_bar_level_changer`) is switched off with `enable_level_changer(false)` on every machine until the shared story flag `GAR_FREE_PASS` exists (`coop_scn_garbage_duty.script`, 1 s tick, re-applied every 15 s). The level has no gate object (checked in level.spawn and all.spawn), so closing the exit is the only way. Since v1.4.2 the SoC guards shooting at players who walk past without a pass is done too (section "Checkpoint zones" below). |
| Pass | Dialog branches: (1) "I need to pass, I have business with the Barkeep" only when the Agroprom case flag `AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO` exists (SoC `agroprom_military_case_have`); (2) NEW, owner approved: "I'd rather pay (2000 RU)" (SoC had 500), money from the talking player (`dialogs.relocate_money_from_actor`, same call as the Cordon bridge bribe), flag for the whole group; "I don't have the money" otherwise; (3) a winning boar attack. After the pass the commander only says the SoC farewell ("Say hi to the Barkeep"). The flag is a normal story flag (saved, synced, late joiners), so the Bar vote / level change and every other story info are untouched.

**Soft-lock guard** (server, every 2 s, on every level, `gate_guard()`): `GAR_FREE_PASS` is also given when (a) the host sets `[garbage] duty_gate = false` in `coop_settings.ltx` (default true, key added to `host_settings`' table; read on the server only, the flag carries it to the clients), (b) the party is on a level past the Garbage story (anything except Cordon, Garbage, Agroprom, Agroprom underground, Dark Valley, X18: so Bar and later, i.e. anybody who has been on the Bar), (c) any story flag with a Bar-or-later prefix (`BAR_ ROS_ MIL_ YAN_ X16_ RAD_ X10_ PRI_ AES_ SAR_ CON_`, taken from `story_flags_table`) exists, which also covers an old save made after the Bar was reached. Once given the flag stays (saved); a host who later sets `duty_gate = true` does not close it again. |
| Boar attack | `gar_smart_terrain_8_m_boar_squad.ltx`: every boar job has `on_death = mob_death@...` with `{=killed_by_actor} %+GAR_DUTY_BOAR_KILLED_n%` (true for every player). When the four boar squads are dead (existing `..._BOAR_n_SQUAD_DEAD` flags) the Scene Director plays `gar_duty_rush` (server trigger, verdict picked once on the server from the flags): `WIN_KILLS` (1, the SoC rule: `gar_boars_counter` takes `c < 1` as the looser) or more kills = praise (`duty_after_rush_good`, `GAR_FREE_PASS` given), none = SoC `gar_actor_looser` ("no use at all", `duty_after_rush_bad`, no pass). SoC itself plays its "normal" line for 1 or more kills and gives the pass through the dialog; here the praise line and the pass come together (project decision). Each client shows the PDA tip (`gar_duty_rush_win|lose`) and plays the SoC voice in its voice language (`coop_soc_opening.voice_lang`, `voice_language` of coop_settings; Russian = the mod's own `characters_voice\scenario\coop_l02_garbage\duty_after_rush_*.ogg`, English = Steam SoC files in the `eng` subfolder). The task "Wave of Mutants" itself is unchanged. |

## Files
`gamedata\scripts\coop_scn_garbage_duty.script` (new), `configs\gameplay\character_desc_coop_l02_garbage.xml`, `dialogs_coop_l02_garbage.xml`, `configs\creatures\spawn_sections_coop_l02_garbage.ltx`
(mod copies + additions), `configs\scripts\coop_l02_garbage\gar_smart_terrain_8_m_boar_squad.ltx`, `gar_smart_terrain_9_walker_duty.ltx`, `configs\text\{eng,rus}\st_garbage_duty.xml`
(new), meshes, one texture, two English voice files. `tools\gen_garbage_fixes.py` makes all config edits (idempotent), `tools\extract_assets.py` the assets,
`tools\add_changes_lines.py` the README lines. The same script also starts Gray's fight (see `garbage_gray\NOTES.md`). Needs `cutscenes_core` (Scene Director) and, for the voice language, `cutscenes_pkg_opening` (falls back to the game language).

## Test plan (single listen host, the live console can teleport and query; Garbage is reached from Cordon by the party vote)
1. Skins: `alife():object("gar_smart_terrain_9")` squads online at the checkpoint (start at about 40, 0.5, 225): list NPCs within 40 m of that point with `npc:section()` and
   `npc:get_visual_name()`; expect `stalker_do_balon_4` for Prapor and balon_8 / antigas / balon_80 for the rest, no `stalker_dolg_N`.
2. Gate closed: `coop_scn_garbage_duty.status()` prints `pass=false`, `changer_ok=true`; teleport next to `gar_bar_level_changer` (-17.1, 0.5, 279.0): no transition prompt / no vote.
3. Talk to Prapor without the case: "Halt" branch, options "I see" and "I'd rather pay (2000 RU)" (with money) or "I don't have the money". Pay with 2500 rubles: money drops by 2000,
   `story_flags.has_flag("GAR_FREE_PASS")` true on host and joined client, `status()` shows `applied=true`, the transition prompt appears at the Bar exit and the vote goes through.
4. Case: `story_flags.give_flag("AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO")` (fresh save), talk to Prapor: "business with the Barkeep" appears, pass given, line "Say hi to the Barkeep".
5. Boars: fresh save, give `GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO`, wait for the 8 boars, kill one or more with the host or a client: `GAR_DUTY_BOAR_KILLED_n` flags counted by `coop_scn_garbage_duty.kills()`;
   when the last boar dies the PDA tip "Excellent..." and the Russian voice play on every machine and `GAR_FREE_PASS` appears. Second run, let the NPCs or mutants kill them all (0 player kills): the "rubbish" tip and voice, no pass.
   Repeat with `voice_language = eng`: the English voice plays.
6. Soft-lock guard (each on a fresh save, `status()` shows `why=`): (a) `duty_gate = false` in coop_settings.ltx, change level to Garbage: exit open, `why=host setting duty_gate=false`; (b) `story_flags.give_flag("BAR_ARNY_ARENA_SMART_TERRAIN_DOG_SQUAD_DEAD_FAIL")` (any BAR_ flag) or start on the Bar and travel back: gate open; (c) load an old save made on the Bar: gate open at once; (d) none of these: `pass=false`, exit closed.
7. Regression: Bar level change by vote after the pass, Gray / Bes quests and the "Wave of Mutants" task completion still work.

## Кратко (RU)
Блокпост Долга на Свалке как в оригинале SoC: солдаты в костюмах Долга (balon_8, противогаз, balon_80), командир Прапор в костюме balon_4 и с диалогом SoC ("Стой, сталкер, дальше тебе нельзя").
Выход к Бару закрыт, пока группа не получит пропуск: документы военных с Агропрома, или 2000 руб. (платит один игрок, пропуск на всех, сохраняется), или победа над кабанами.
После нападения кабанов командир говорит оригинальным голосом (русским или английским по настройке голоса): хотя бы один убитый игроками кабан - похвала и пропуск (правило SoC: счётчик меньше 1 = "пользы от тебя ноль"), ни одного - упрёк и без пропуска.
Защита от тупика: выход открывается сам, если сюжет уже ушёл дальше Свалки (Бар и дальше, флаги BAR_/ROS_/... в старом сохранении) или хост выключил `[garbage] duty_gate = false` в coop_settings.ltx.
Не проверено в игре.

## Update 2026-10-21: quests (patch garbage_soc_quests)
The commander dialog `gar_duty_pass_start_dialog` and the Seriy dialogs of this patch were extended by `garbage_soc_quests` (report branch with the 1500 reward, the SoC favor "What's the favor?", SoC wording for Seriy). The commander's job `gar_smart_terrain_9_walker_prapor.ltx` had `meet = no_meet` (no talk possible at all); `garbage_soc_quests` ships a talkable copy. See `garbage_soc_quests\NOTES.md`.

## Checkpoint zones (v1.4.2, as in SoC)
SoC (Steam 1.0006, `gulag_garbage.ltx`, `xr_meet.script`, level.spawn of `l02_garbage`): the three zone guards of `gar_dolg_blokpost` (`zoneguard1..3`) have the meet parameter
`zone = gar_dolg_blokpost_zone_warn|{-gar_free_pass}<state>@{-gar_free_pass}gar_dolg_blokpost|gar_dolg_blokpost_zone_guard|{-gar_free_pass}true@{-gar_free_pass}gar_dolg_blokpost`.
`xr_meet` reads it for the actor: in the warning zone the guard takes the state `backoff` (guard 1) or `threat` (guards 2, 3) and plays the sound group `gar_dolg_blokpost`
(`duty_zoneguard_1.ogg`); in the guard zone the state is `true`: a zero-power wound hit by the actor and `set_relation(enemy, actor)`, so the guard attacks. Both only while the
info `gar_free_pass` is not set. Zones (SoC level.spawn space restrictors, no logic of their own): `gar_dolg_blokpost_zone_warn` box 24.22 x 8.15 x 10.23 m at (28.32, 4.23, 232.59) yaw 1.0242;
`gar_dolg_blokpost_zone_guard` box 6.31 x 3.96 x 12.9 m at (21.03, 2.36, 237.08) yaw -0.5292 (both long sides follow the road to the Bar; the Garbage of the mod has the same coordinates).
Co-op (`coop_scn_garbage_duty.script`, 250 ms tick):
* SERVER, every player on his own, only while `GAR_FREE_PASS` is missing: a player inside the guard zone makes every Duty NPC of the checkpoint (spawn section `gar_dolg_blokpost`, the
  8 guards; the commander has his own section and is left out because the pass dialog needs him) an enemy of THAT player only (`set_relation(game_object.enemy, his object)` is a
  per-pair relation, the other players keep talking to the guards), with SoC's zero-power wound hit. Re-applied every 5 s while he stays (guards that come online later).
* The moment `GAR_FREE_PASS` exists (dialog, case, boars, soft-lock guard) every hostile guard goes back to neutral for every player: never after the pass.
* Soft-lock guard: a hostile player who is more than 60 m from the checkpoint and out of the guard zone for 15 s is forgiven (SoC itself never forgives, but SoC has no party that needs to
  come back and talk to the commander), a dead player's entry is dropped (new object, no relation left).
* EVERY MACHINE, local player only: in the warning zone or the guard zone, without the pass, the guard warning voice `duty_zoneguard_1` plays on his machine (own language like the other
  voices: Russian = the mod's own file at `sounds\characters_voice\scenario\coop_l02_garbage\`, English = SoC file under `...\eng\`, shipped here), once per 25 s.
  The guard postures (backoff / threat) are not reproduced: the guards' jobs here are `walker` jobs with `meet = no_meet` and `invulnerable = true` (unchanged).
Offline: `tests\zones_mock_test.py` (real script in a Lua VM, geometry, per-player hostility, commander left out, pass undoes it, calm-down, voice per language): ALL PASS.
Not run in the game (offline task); the first live check is `coop_scn_garbage_duty.status()` (`hostile=` count) and walking a player into the guard zone with the pass flag missing.
Кратко (RU): как в SoC: без пропуска игрок в зоне предупреждения слышит окрик охраны Долга (оригинальный голос), в зоне охраны (6 x 13 м на дороге к Бару) весь караул Долга становится враждебным
именно к этому игроку (остальные игроки не затронуты; командир остаётся нейтральным, он нужен для диалога). С пропуском (`GAR_FREE_PASS`) охрана снова нейтральна. Не проверено в игре.

## 1.4.3 fix: crash on Garbage, "Can't open section 'kombez_antigas_damage'"
The SoC Duty meshes of the checkpoint (`stalker_do_antigas`, `stalker_do_balon_4`, `stalker_do_balon_8`) name the capture files
`models\capture\kombez_antigas_damage_low` / `kombez_mask_damage_low`, and those named the bone protection sections `kombez_antigas_damage` /
`kombez_mask_damage`, which no config defines (not in the mod, not in xrMPE, not in CoP). An NPC reads that section when its model loads, so the
game crashed as soon as the checkpoint guards came online. Now: `stalker_dolg_4` (gas mask) and `stalker_dolg_1` (balloon mask), the mod's
own Duty protection sections. Checked for every .ogf of the release stage with a scan (capture file exists, its sections exist): the only other
misses are player outfit meshes (`stalker_hero_captures` -> `gilet_mask_damage`, a CoP original file; `kombez_kupol_damage`), which players have
worn since v1.4 without a crash (players do not use that section); left as they are.
