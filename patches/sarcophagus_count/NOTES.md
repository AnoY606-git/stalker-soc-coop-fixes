# sarcophagus_count: original-SoC Monolith count, no Preacher

## Original SoC (reference: l12u_sarcofag)
- `scripts\l12u_sarcofag\npc\` has 12 level-placed Monolith (`sar_stalker_monolith_0019`, `_high`, `_high_0000` .. `_0009`).
- `soc_npc\` + `misc\soc_spawner_l12u_sarcofag.ltx`: 8 more Monolith in the secret room, spawned only after the decoder
  finished decoding (flags `SAR_MONOLITH_SPAWN1..8` set by `sar_decoding.ltx`). About 20 in total.
- No Preacher and no fanatics anywhere in SoC. The decoder is an item you find in the level (`actor_has_decoder`), the secret
  door `sar_door.ltx` opens after decoding.

## Cause in the mod
- `squad_descr_coop_l11_sarcofag.ltx` had 86 NPCs: 21 patrol squads of 1-6 (70 NPCs), 3 squads of 3 behind the decoder door
  (9) and the Preacher squad + 6 fanatic squads at smart 17 (7). Roughly 4x the original.
- The Preacher carried the quest item `dev_decoder`; quest chain and door were tied to his death flag.

## What this patch does
1. **Count**: 21 patrol squads of 1 (smart 8, the biggest area: 2) = 22, plus the 3 squads behind the decoder door of 2 each
   = 6, total 28 (SoC about 20, so about 1.4x for co-op). Every squad keeps its name, `story_id`, `spawn_point` and
   `on_death`, so `SAR_SMART_TERRAIN_18_ORDINARY_MONOLITH_N_SQUAD_DEAD` still fires. Squads behind the door still come one at
   a time (each spawns after the previous died), as before. Smart terrains have fewer members than jobs, which is safe.
   No respawn: the Sarcophagus smart terrains have no `respawn_params`; each squad is created once by its restrictor
   (`create_squad` + a STOP flag).
2. **Preacher and fanatics removed**: their 7 squads are gone from `squad_descr` and from `[start_position_coop_l11_sarcofag]`
   in `simulation.ltx` (the section header is kept, empty). The spawn restrictor of smart 17 now spawns the `dev_decoder`
   item (`spawn_object`, same pattern as the bandit chainmail on Cordon) at the Preacher's old walk path. The voice scene
   restrictor and the 6 fanatic teleport particle restrictors are replaced by empty (`sr_idle@nil`) logic. The 3 smart 18
   teleport particles no longer wait for the (never set) Preacher flag.
3. **Progression kept**: task 1 (reach the Monolith) now gives the decoder task directly (the kill-the-Preacher task is
   skipped); the decoder task text says "Find the decoder"; the door `sar_codedoor_left_decoder` needs only
   `=actor_has_item(dev_decoder)` (no Preacher flag). After that everything is as before (LOCKED_START_OPEN_INFO, 3 waves,
   door opens when they are dead).
4. **player_scaling does not stack**: `skip_levels = coop_l11_sarcofag` is checked in `eligible()` (members) and in
   `reinforce()` (extra squads), so counts stay as above for any number of players.
5. **optional/sarcophagus_fps**: `sarcophagus_wave_percent` default changed 55 -> 100 (script default and `sarcophagus_fps.txt`),
   README adjusted. With squads of 1-2 the trim keeps `ceil(n*pct)` anyway, so at 55 it would only have changed nothing but
   extra noise; 100 avoids double reduction.

## Files (all under `gamedata\`)
- `configs\misc\squad_descr_coop_l11_sarcofag.ltx`, `configs\misc\simulation.ltx` (db0 copy minus 7 lines; no other patch ships it)
- `configs\misc\tm_coop_l11_sarcofag.ltx` (included by repeatable_quests' task_manager.ltx; that patch does not ship this file)
- `configs\scripts\coop_l11_sarcofag\doors\sar_codedoor_left_decoder.ltx`
- `configs\scripts\coop_l11_sarcofag\space_restrictors\`: `sar_smart_terrain_17_spawn_squad_...`, `sar_monolith_preacher_say_...`,
  `sar_start_teleport_npc_1..6_...`, `sar_smart_terrain_18_start_teleport_npc_1..3_...`
- `configs\text\eng|rus\st_coop_l11_sarcofag_quest.xml` (windows-1251, edited as bytes)
- No overlap with `cutscenes_pkg_endings` (it ships `sar_monolith_space_restrictor.ltx`, untouched here).
- Left in place, now unused: Preacher/fanatic character descriptions, spawn sections, profile entries, smart 17 jobs/animpoints.

## Arrival crash fix: Sarcophagus coop respawn points (`gamedata\levels\coop_l11_sarcofag\level.game`)
The engine's round start after every level change calls `game_sv_Deathmatch::assign_RP`. Coop uses RPoints with team 4, game_type 128
(chunk 0x2000 of `level.game`); all other levels have 4 of them (escape: ids 6..9), the Sarcophagus had none, so any arrival
(guide teleport, not only the test harness) crashed the server about 7 s after the load. The patched `level.game` adds 4 team-4/gt-128
RPoints at (-32.2, 0.2, 42.7) (+-0.8), where the player appeared on arrival. chunk 0x1000 (patrols) is unchanged.

## Test results (test/hooks_sarc.lua, run_coop -Mode listen -Clients 1 -Cfg no_respawn=1, lane copy): 38 PASS, 0 FAIL, no crash
Travel: Cordon Globus flag + vote + `xrmpe_teleport_actors`. Passed:
- level loaded; 22 Monolith in 21 squads (band 20..30); no preacher/fanatic objects; preacher story id absent;
- exactly one `dev_decoder` on the ground at (23.8, 56.0, 26.6); quest marker target `sar_codedoor_left_decoder` resolves;
- `actor_has_item(dev_decoder)` true; wish flag -> task `sar_start_get_to_the_monolith` completes -> decoder task completes with the
  decoder -> `SAR_START_OPEN_THE_DOOR_TO_MONOLITH_MANAGEMENT_QUEST_TASK_INFO` set (the first task is given by the hook, as the
  CNPP-1 task would do on a real arrival);
- door used with the decoder (`door_action:use_callback`, the real on_use path): `ph_door@locked_start_open_idle` ->
  `ph_door@locked_start_open`, `LOCKED_START_OPEN_INFO` set;
- waves 1, 2, 3 each spawn with 2 members one after the other; after each squad death (`squad:on_npc_death`, the call a real kill
  ends in) `SAR_SMART_TERRAIN_18_ORDINARY_MONOLITH_N_SQUAD_DEAD` is set; after wave 3 the door goes to `ph_door@open` and
  `door_action:is_open()` is true.
Not covered: the combat kill itself (death callback called directly), and the CNPP-1 `aes_1_level_changer` route (the xrMPE level
changer binder is disabled; level changes only happen through the guide vote).

## Quest marker (code only, UNTESTED)
The decoder task `sar_start_search_the_preacher_body_and_retrieve_the_decoder_quest_task` now has `target = sar_codedoor_left_decoder`
(its story id resolved in game, 8864) instead of the removed Preacher. Not tested in game; the unused kill-the-Preacher task keeps its old target.

## Кратко по-русски
В оригинальном SoC в Саркофаге около 20 бойцов Монолита (12 на уровне + 8 в тайной комнате) и нет Проповедника.
Теперь: 22 бойца на патрулях + 3 группы по 2 за дверью декодера = 28 (около 1.4x от оригинала). Проповедник и 6 фанатиков
удалены; декодер лежит на уровне там, где стоял Проповедник; квест и дверь больше не требуют смерти Проповедника.
Масштабирование по числу игроков в Саркофаге отключено (skip_levels). Опциональный FPS-фикс по умолчанию теперь 100%.
