# level_back: a way back from the Radar and from Pripyat

Request (FOSTER, agreed with Akasi): when travelling to the Radar there is a message that you cannot go back, and there is no way back from the Radar
and from Pripyat. Make both possible like in the original SoC, without breaking the story.

## What was wrong
| Question | Answer (read from the mod's `all.spawn`, scripts and configs, and from the original SoC `level.spawn` files of the Steam install) |
|---|---|
| The message | `st_test_text_yes_no` "Are you ready to travel to the Center of the Zone? There will be no turning back." (RU "Обратного пути не будет."). It is shown by the question restrictor `mil_question_1_space_restrictor` on the Army Warehouses (`configs\scripts\coop_l07_military\space_restrictors\mil_question_1_space_restrictor.ltx`, answer yes = `xrmpe_teleport_local_actor(mil_smart_terrain_12_yes_temp_1_walk)`, a point inside `mil_rad_level_changer`). It is the only object that uses the string. |
| The one-way transitions | Nothing is disabled by script and no `enable_level_changer(false)` or restrictor closes them: the level changer objects are simply NOT in the mod's `all.spawn`. The mod has `mil_rad_level_changer` (Army Warehouses -> Radar), `rad_level_changer_1` (-> X-10), `rad_level_changer_2` (-> Pripyat), `x10_level_changer` (X-10 -> Radar), `pri_level_changer` (Pripyat -> CNPP) but no Radar -> Army Warehouses and no Pripyat -> Radar. |
| Original SoC | `l10_radar`: `exit_to_military_01` (562.4 -53.8 -421.8), `exit_to_pripyat_01`, `exit_to_bunker_01`; `l11_pripyat`: `exit_to_radar_01` (13.3 -2.4 -297.3, a 259 m wide wall on the south edge), `exit_to_stancia_01`. SoC has NO direct Radar - Bar link: the way back from the Radar is Radar -> Army Warehouses -> Bar (the mod has `mil_bar_level_changer` / `bar_mil_level_changer`). The Bar is reached in two hops, as in the original. |
| Brain Scorcher | The psi field is only the story flags `X10_LAB_PRIMARY_SWITCHER_1/2_DEACTIVATE_INFO`: the `rad_psi_radiotion_*` restrictors switch to `sr_psy_antenna@nil` (intensity 0) when both exist, and the scene `radar_stop` is `once`. Flags are saved and shared, so a trip back and forth neither resets the state nor replays the scene. |

## What changed
1. `gamedata\configs\text\{eng,rus}\ui_st_screen_addon.xml` (owned by `lobby_text`, edited there): `st_test_text_yes_no` is now "Are you ready to travel to the Radar?" /
   "Готовы ли Вы отправиться к Радару?". The dialog stays (it is the confirmation of the walk to the Radar), only the "no turning back" sentence is gone.
2. Two new level changers in `spawns\all.spawn`, written by `tools\add_level_changers.py` (an idempotent in-place step like `no_tech_parts\tools\strip_spawn.py`;
   see its header for the pipeline order; it was applied to `darkvalley_restore\gamedata\spawns\all.spawn` and to the skipped `soc_levels` copy):

| Object | Level | Where | Arrival | Why there |
|---|---|---|---|---|
| `rad_mil_level_changer` | `coop_l09_radar` | SoC `exit_to_military_01`: 562.4 -53.8 -421.8, the original angles, box 11.3 x 11.4 m wide, 1.6 m deep (the original is 3.4 m deep: the arrival point of Army Warehouses -> Radar (564.9 -53.7 -415.8) is 2.9 m in front of that box, with the thinner box it is 4.7 m) | `coop_l07_military`, game vertex 1529 (52.6 -18.4 361.6), node 352872: the vertex next to the point where the old question sends players that say "no" (54.9 -18.5 354.7), 16.8 m in front of `mil_rad_level_changer` | the original exit; the Radar start is the edge of the map |
| `pri_rad_level_changer` | `coop_l10_pripyat` | 14.0 -2.4 -304.5, box 62 x 15 x 2 m (SoC `exit_to_radar_01` is at -297.3 and 259 m wide, but the mod's arrival from the Radar, 26.6 -2.2 -296.8, lies INSIDE that wall: it would send players straight back, so the wall moved 7 m south and shrank to the walkable width, the arrival is 6.7 m in front) | `coop_l09_radar`, game vertex 1749 (384.0 -34.0 141.9), node 114380: 18 m in front of `rad_level_changer_2` (the Pripyat exit) on the Radar side | SoC: `start_actor_02` of the Radar is next to `exit_to_pripyat` |

   Both are clones of an existing changer (same packet layout, `level_changer_invitation` hint, enabled), story id = name, own game vertex = cross table of the own node.
   `aes_2_esc_freeplay_level_changer` (CNPP-2 -> Cordon rookie village) is added by the same tool for the patch `freeplay`.
3. `arrival_facing` (skipped patch) knows the two new changers.

Not done on purpose: the other forward-only exits of the original game stay forward only (Pripyat -> CNPP, CNPP chain, Cordon -> Dark Valley; SoC has no way back
there either, the checker lists them as `ONE_WAY`). X-10 already has its way back (`x10_level_changer` -> Radar).

## Psi field and the story when walking back
- Army Warehouses exit of the Radar: inside the 5 % belt only (`rad_psi_radiotion_5`, hit 5), the same place where players arrive coming from the Army Warehouses; the 30 %
  sphere ends 165 m away, the 55 and 100 % zones 350 m and 540 m away. Nothing new happens there.
- Pripyat -> Radar arrival: inside the 5 % and 30 % spheres, outside the 55 % one (41 m). With the Brain Scorcher off (the normal way: the Pripyat gate needs X-10) the
  zones are off by the flags; with it still on (the party jumped to Pripyat with the Cordon guide) the 30 % field applies as in SoC, not lethal at once. SoC behaviour kept.
- The returning players re-enter levels whose logic is saved (no `type = no_save` in the Radar, X-10 and Pripyat restrictors) and whose director scenes are `once`
  (`radar_stop`, `pri_stadium_fly`): the in-game hook asserts that the set of `SCN_*_PLAYED` flags is the same before and after a round trip.

## Checks
- `python patches\level_back\tools\check_level_changers.py <all.spawn> --addon <coop.addon> [--all-levels]` (or `--ai-dir <dir with levels\<level>\level.ai>`): for every changer a valid
  destination level / game vertex / node / position, the arrival on the AI mesh (within 1.6 m of the node), the changer standing on the mesh, no arrival point inside any
  changer box of its level and a clearance of at least 3.5 m for the new ones (2 m for the old ones, warnings only), both directions (listed one-way exits excepted), the
  three new objects present and enabled. Result on the shipped file: `0 FAIL, 24 NOTE` (the notes are old objects of the level maker: arrival 1.3 to 1.7 m from a box, own
  node 4 to 44 m from the object, no mesh node inside a thin box; none is touched), `LEVEL CHANGERS OK`.
- `add_level_changers.py --check <all.spawn>` exits 1 when one of the three is missing; `no_tech_parts\tools\strip_spawn.py --check` and
  `bar_arrival_anomalies\tools\strip_bar_anomalies.py --check` still pass on the file (the steps compose).
- Game hook (not run here, offline task): `tests\level_back_hooks.lua`, see the header; asserts for the Radar and for Pripyat that the back changer exists on the server, is
  enabled and online, the old forward changer is still there, no "no turning back" text (EN and the cp1251 RU bytes), then every player is teleported into the back changer, arrives
  on the level behind, is alive, all players came along, the story flags (marker, both Brain Scorcher flags) are intact, the SCN_*_PLAYED set is equal, and the old forward
  changer takes the party to the target level again.

## Run (listen mode, host + 1 client)
```
cd <repo>
python build.py <out>\zzz.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner lbrad -Mode listen -Clients 1 `
  -DbFile <out>\zzz.db -Hooks <repo>\patches\level_back\tests\level_back_hooks.lua -Cfg no_respawn=1 -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir>
python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix LB --require 24
```
The ready-made saves of `tools\stalker_xrmpe\live\saves` do NOT contain the new objects (their server state was made with the v1.3 `all.spawn`), so the runs start on a fresh Cordon and travel. Quick manual check with the live console instead of a hook (fresh start, `-DbFile <out>\zzz.db`): `live.travel('rad')`, then `lua.ps1 "alife():object('rad_mil_level_changer').position"` and `live.tp(562.4, -53.8, -421.8)` (moves every player into the back changer; the answer after the level change).
For Pripyat make a copy of the hook with `local DEST = "pri"` (run_coop takes one `-Cfg` only) and use `-Owner lbpri`. The hook travels Cordon -> target with the guide vote
(about 70 s per level change).

## Кратко по-русски
Сообщение "Обратного пути не будет" - строка `st_test_text_yes_no` у вопросника `mil_question_1` на Армейских складах; теперь там "Готовы ли Вы отправиться к Радару?".
Обратные выходы не были выключены скриптами: самих объектов level changer не было в `all.spawn` (Радар -> Армейские склады, Припять -> Радар). Добавлены по оригинальной ТЧ:
`rad_mil_level_changer` (`exit_to_military_01` на Радаре) и `pri_rad_level_changer` (`exit_to_radar_01` в Припяти, стена сдвинута на 7 м, потому что точка прихода с Радара лежала
внутри оригинальной стены). Прямого перехода Радар - Бар в ТЧ нет: путь Радар -> Армейские склады -> Бар. Состояние Выжигателя мозгов хранится в сюжетных флагах и при возврате не
сбрасывается, сцены `once` не повторяются. Проверка: `tools\check_level_changers.py`, игровой тест `tests\level_back_hooks.lua`.

## Run 2026-10-21 (Radar case)
`rad_mil_level_changer` and `pri_rad_level_changer` are in the shipped `all.spawn` (the build ships darkvalley_restore's copy, byte for byte; `add_level_changers.py --check`
3 of 3, `check_level_changers.py` 0 FAIL). In the game run the back changer existed on the server, was enabled, the party travelled Radar -> Army Warehouses through it and forward again
through the old one, with every story flag and scene kept. The one FAIL ("online on this level") was the test: `level.object(<name>)` returns nil for level changers in xrMPE. The hook now looks the
client object up by id and only logs when it is missing; the teleport step proves the changer works.

