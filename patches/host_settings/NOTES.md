# host_settings: one settings file the HOST edits (coop_settings.ltx)

## Why
The tuning numbers (player damage, enemies per player, box loot, ...) lived in ltx files inside `zzz_soc_coop_fixes.db`, which sits inside `coop.addon`.
Changing one meant rebuilding the db and giving every player the same new file. Numbers that only the server uses do not have to be in the add-on:
this patch reads them from a plain text file in the host's app data folder. That file is not part of the add-on, so it does not change the add-on
checksum and the other players need nothing.

## Where the file is
`coop_settings.ltx` in `$app_data_root$` (the engine reads `fsgame.ltx` / `fsgame_s.ltx` in the game folder):
- host who also plays: `X-Ray Multiplayer Extension\game\_appdata_\coop_settings.ltx`
- dedicated server: `X-Ray Multiplayer Extension\game\_appdata_server\coop_settings.ltx`
- test harness: `<game>\_appdata_qa_<tag>_A\coop_settings.ltx` (listen host) or `..._S\` (dedicated role)

On the first server start without the file, `coop_host_cfg` WRITES it: every host-editable setting, its current db default (read from the db ltx, so the
file always starts equal to what ships) and two comment lines (EN, RU). The file is read again at every level start (the Lua VM restarts), so a host
edits, saves and changes level. A missing key, a missing file or a value that does not parse (`banana`) uses the db default and logs the bad value once.
Comments start with `;`, section and key names are not case sensitive, `1,5` works as `1.5`, true/false also as yes/no/on/off/1/0.
After a patch update that adds new settings, old lines keep working and the new keys use their db defaults; delete the file to get a full fresh copy.

## Module
`scripts\coop_host_cfg.script`:
- `coop_host_cfg.num(section, key, default)`, `.bool(...)`, `.str(...)`: the value from the file, else `default`. On a machine that is not the server
  (`OnServer()` false, a joined client) they return `default` at once and never touch the file.
- `coop_host_cfg.reload()` re-reads the file and makes every consumer drop its cache (`host_reload()` in each consumer); tests use it.
- Start log: one line per read, `[HOSTCFG] host settings v1 coop_settings.ltx [file created with the defaults | file read (N settings in it)]: X value(s)
  from the file, Y from the db defaults, Z bad; effective: section.key=value(file) ...` in the engine log and in `logs\host_cfg.log`
  (a value from the file is tagged `(file)`, a bad one `(bad value 'x', default used)`). The consumers keep their own lines too
  (`[CBAL] coop_balance config`, `[PSCALE] player_scaling ... config`).
- The setting table (sections, keys, EN/RU comments) is the `build_groups()` function. The Russian texts are stored as UTF-8 decimal escapes so the
  script stays ASCII (`tools\luabal.py` reads cp1251); `tools\ru_escape.py --decode/--encode` converts them for editing.

## Which settings the host can edit (server only, safe)
| Section in the file | Keys | Consumer (patch) | Default from |
|---|---|---|---|
| `[damage]` | player_damage_mult, log | `coop_balance.cfg()` (soc_economy) | `misc\coop_balance.ltx` |
| `[ammo]` | ammo_per_extra_player, max_players | `coop_balance.cfg()` | same |
| `[enemy_scaling]` | enabled, human_extra_per_player, mutant_extra_per_player, max_factor, max_extra_members, extra_squads_per_player, reinforce_cooldown_s, reinforce_first_delay_s, reinforce_min_distance, skip_levels, log | `player_scaling.cfg()` (player_scaling) | `player_scaling.ltx` |
| `[box_loot]` | enabled, fallback_breakable, fallback_inventory, wood_chance, metal_chance, inventory_chance, items_per_roll, ammo_min, ammo_max | `stash_loot.config()` (stash_loot) | `misc\box_loot.ltx` `[settings]` |
| `[garbage]` | duty_gate (true = the Garbage exit to the Bar is closed until the group has a pass; it opens by itself once the story is past the Garbage) | `coop_scn_garbage_duty` (garbage_duty) | script default true |
| `[freeplay]` | enabled | `coop_scn_freeplay.enabled()` (freeplay) | script default true: true = after the true ending the party plays on at the Cordon rookie village (inventory and story flags kept), false = credits and main menu as before |
| `[box_loot_items]` | bread, kolbasa, conserva, vodka, bandage, medkit, antirad, ammo (weights, 0 = never) | same | `[consumables]` |
| `[repeat_quests]` | cooldown_min, timeout_mult, item_rewards | `coop_repeat_quests.load_cfg()` (repeatable_quests) | `misc\coop_repeat_quests.ltx` `[defaults]` (the last two are new, defaults 1 and true) |
| `[mutant_loot]` | the 12 `mutant_*_part` chances, take_distance | `mutant_loot.chance_for()` / `take()` (mutant_loot) | `misc\mutant_loot.ltx` |
| `[roaming]` | enabled, start_delay, stay_min, stay_max, max_moving, go_home_chance, min_players_dist, allow_online_move, mutants | `alife_roaming` load_cfg (alife_roaming) | `misc\alife_roaming.ltx` `[roaming]` |
| `[sarcophagus_fps]` | corpse_limit, sarcophagus_corpse_limit, sarcophagus_wave_percent (only when the optional package is in the db) | `sar_fps_cfg.get()` (optional\sarcophagus_fps) | its own defaults, then the old `sarcophagus_fps.txt` (still read; the new file wins) |

Why these are server-only: the hit callbacks that apply the damage extra, the trader ammo stock, squad creation (`sim_board`), box and mutant loot rolls,
repeatable-quest ticks (`OnServer()` guard in `update()`), roaming (`sim_squad_scripted:update`) and the corpse/wave logic all run on the server, and what they
create is replicated to the clients. `coop_balance.on_npc_hit` got an `OnServer()` guard so a client can never apply a multiplier of its own.

## What stays in the db (must be identical on every PC, or unsafe to change)
- **Task manager rewards** (`reward_money` in `tm_coop_*.ltx`, `tm_coop_repeat.ltx`, task icons/titles): read by the task manager and the task UI on every machine.
- **Quest structure** of the repeatable quests (accept/done/fail info flags, spawn lists, `reward_items` per quest, dialogs, texts): the clients' dialogs and tasks depend on it.
- **player_scaling safety limits**: `hostile_factions`, `skip_smarts`, `max_extra_squads_per_smart`, `slot_fraction`, `slot_margin`. A wrong value overflows a smart terrain's job slots
  (`Insufficient smart_terrain jobs`, `job_data nil` crash). Also `squad_descr_pscale.ltx`.
- **roaming safety limits and route data**: `max_npc_per_smart`, `max_squads_per_smart`, `max_mutant_squads_per_smart`, `max_squad_size`, `communities`, and the per-level `group_*` / `use_*` lines.
- **box_loot ammo tiers** (`[tier_*]`): lists of section names, not numbers; kept in the db.
- **Trader supply sections** (`supplies_start_ammo`, price/discount in the trader ltx files): trade windows are built on the clients too.
- **Client-side visuals and UI** (`lumscale_presets`, `socfx_mm.ltx` main menu style, cutscene configs, textures, sounds, spawns, levels): clients read them.
- The sarcophagus_fps package itself (`damages.ltx`, `m_stalker.ltx`, character descriptions) changes game data and is part of the add-on; only its three numbers are host-editable.

## Offline check (no game)
`python patches\host_settings\tests\host_cfg_mock_test.py` (needs `pip install lupa`, same as `qa_lib_mock_test.py`): runs the real `coop_host_cfg`, `coop_balance`,
`player_scaling`, `stash_loot`, `mutant_loot`, `coop_repeat_quests`, `alife_roaming` and `sar_fps_cfg` in a Lua 5.1 VM with a small engine mock and the real ltx files.
It proves file creation with all settings, the overrides in every consumer, bad value / missing key / comment / BOM / CRLF / decimal comma handling, a client that ignores the file,
an unwritable folder, and it runs `tests\host_cfg_test.lua` against the same mock (33 asserts).

## In-game test (one listen-host run, Cordon)
Hook `tests\host_cfg_test.lua`. The harness creates a fresh `_appdata_qa_<tag>_A\` so the file does not exist at the server start; the hook then writes the file itself
and calls `coop_host_cfg.reload()` (no harness change and no `-Cfg` needed).
```
cd <repo>
python build.py <out>\zzz.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner hostcfg -Mode listen -Clients 1 `
  -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\host_settings\tests\host_cfg_test.lua -SoakSeconds 170 -CompareTimeout 10 -ResultDir <dir>
python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix HC --require 33
```
Expected (host = role A, `client_A\qa_assert.log` and the profile's logs):
1. `HC file exists after the first server start`, `... holds the db defaults`, `... every section`, `... EN and RU comment lines`, `host_cfg.log: the first start CREATED the file` (log line `file created with the defaults`).
2. Phase A (`player_damage_mult = 1.0`): `[HOSTCFG] ... damage.player_damage_mult=1(file)`, `[CBAL] coop_balance config: damage_mult=1.00`, hits to kill N1 (3 expected, `qa_events.log`: `HC phase A hits to kill (mult 1.0): 3`).
3. Phase B (`player_damage_mult = 3.0` and the other overrides): `[HOSTCFG] ... damage.player_damage_mult=3(file)`, `[CBAL] coop_balance config: damage_mult=3.00`, `HC phase B hits to kill (mult 3.0): 1`
   and the assert `fewer hits than phase A` (B < A); box loot `wood 100 / metal 0`, medkit gone, vodka 77, `max_factor` 1.75, dog part chance 1, repeat quest cooldown 60.
4. Phase C: `bad value 'banana'` in the start line, the db default 1.5 back, `max_players 3` still applied, file deleted and written again with `player_damage_mult = 1.5`.
Last line of the hook: `HC done` in `qa_events.log`. Any `FAIL` line fails the test. The damage probe depends on the existing `coop_balance` hit path (see `patches\soc_economy\tests\damage_probe.lua`), not on this patch.

## Русский (кратко)
Числа баланса, которые использует только сервер (урон игроков, враги на игрока, добыча из ящиков, части мутантов, повторяемые задания, ходящие отряды), теперь можно менять в простом файле
`coop_settings.ltx` у ХОСТА, без пересборки db. Файл лежит в `X-Ray Multiplayer Extension\game\_appdata_\` (хост играет) или `_appdata_server\` (выделенный сервер) и создаётся автоматически
при первом запуске со всеми настройками, значениями по умолчанию и комментариями EN/RU. Остальным игрокам файл не нужен, отпечаток аддона не меняется. Неверное или отсутствующее значение
= значение из db. Файл читается заново при каждой смене локации. В лог пишется строка `[HOSTCFG]` со всеми действующими значениями (из файла помечены `(file)`).
В db остаётся всё, что должно совпадать у всех (награды деньгами, структура заданий, UI, текстуры) и опасные пределы (слоты смарт-терренов).


## Personal `[client]` section (2026-10-21): the one part every player reads
The file above is for the host. One section is different: `[client]` holds PER-PLAYER settings that are read on EVERY machine, also on a client that only joins a game, from that machine's own `coop_settings.ltx` (`_appdata_` of the player). Server behaviour is unchanged: `num` / `bool` / `str` still return the default at once on a non-server machine and never touch the file; `damage`, `ammo` ... are still read by the host only.

| Section | Key | Values | Default | Consumer |
|---|---|---|---|---|
| `[client]` | `voice_language` | `auto`, `rus`, `eng` | `auto` | `coop_soc_opening.voice_lang()` (patch cutscenes_pkg_opening): voice of Sidorovich's opening speech and start dialog. `auto` = follow the game language; a line with no recording in the chosen language is silent. |

- API: `coop_host_cfg.client_str(key, default)`. On the server (a host who also plays) it reads the normal parsed file; on any other machine it reads its own file by itself.
- Writing: the first server start writes the full file including `[client]` (the group is the first one in the file, EN + RU comment lines). A machine that is not the server and has no file gets a small file with just the header and the `[client]` section. An existing file (also an older v1.4 test file) without `voice_language` gets the `[client]` block APPENDED (its other lines are untouched); a section appended on the host is parsed at the next read (next level start). Log lines: `[HOSTCFG] client settings coop_settings.ltx [file created | file read | file read, [client] section appended]: path=...` (`logs\host_cfg.log`).
- Values are trimmed, case does not matter, `;` starts a comment; the consumer accepts `russian` / `ru` and `english` / `en` as well and treats anything else as `auto` (logged once as `SOCOPEN VOICE bad voice_language`).
- `reload()` also drops the client state. The setting count in the start line is now 58 (was 57).
- Offline: `tests/host_cfg_mock_test.py` has the new cases (client with and without file, appended section, BOM / case / comment, host with an old file, fresh file); all pass together with the old ones.

### Кратко (RU)
Раздел `[client]` в coop_settings.ltx личный: его читает КАЖДЫЙ игрок из своего файла (в том числе тот, кто только подключается). Сейчас там один ключ `voice_language = auto | rus | eng` (язык озвучки вступления Сидоровича, по умолчанию auto = язык игры). Файл или раздел создаётся при первом запуске (старый файл дополняется в конце, остальные строки не трогаются). Остальные разделы по-прежнему читает только хост.

### Свободная игра (2026-10-21)
Новый раздел `[freeplay]` (ключ `enabled`, по умолчанию true): после истинной концовки группа возвращается на Кордон и играет дальше; false = титры и главное меню, как раньше (патч freeplay).
