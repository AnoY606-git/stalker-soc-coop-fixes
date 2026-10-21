# corpse_artifacts - artifacts in the backpacks of dead stalkers (the original SoC bug, fixed)

Status: written and checked offline (Lua VM with the real script and the real tables, see "Offline check"). Not run in the game yet (test plan below).
Requested by the maintainer (FOSTER).

## The vanilla bug (original S.T.A.L.K.E.R.: Shadow of Chernobyl 1.0006, files read from its archives)
The wiki says: like all artifacts of the last price tier, "Battery" (`af_dummy_battery`) was meant to appear with a 0.5% chance in the backpacks of some NPCs
when certain conditions are met, but because of an error in the game code it never appears on dead stalkers. Cause, in `scripts\death_manager.script`
and `configs\misc\death_items_by_communities.ltx`:
- The ltx gives every artifact a chance as a fraction: `[stalker]` lists 0.015 (first tier of a group), 0.01 and 0.005 (last tier). The script turns it
  into a percent: `item_by_community[community][id] = 100 * tonumber(value)`, so the last tier becomes **0.5**.
- The roll is `if math.random(100) <= rnd then alife():create(...)`. `math.random(100)` returns an INTEGER from 1 to 100, so `<= 0.5` is never true.
  There is no typo and no wrong section name: a fractional percent cannot be rolled with an integer roll. The same roll turns 1.5 into 1 (the 1.5% tier really
  drops at 1%, measured 1.08%) and 1.0 into 1 (1%), so only the 0.5% tier is dead.
- 0.5% artifacts in SoC (`[stalker]`, inherited by `bandit`, `killer`, `ecolog`, `dolg`, `freedom`): `night_star, gold_fish, soul, electra_moonlight,
  rusty_sea-urchin, ameba_mica, cristall, dummy_glassbeads, dummy_pellicle, dummy_battery, dummy_dummy, dummy_spring, fuzz_kolobok` (13). This mod has no
  `af_dummy_dummy_soc` twin, so 12 can drop here. Reproduced offline with the original SoC script and tables: 40000 corpses on Radar, 0 of the 13 ever dropped,
  `af_medusa` (0.015) 1.08%.
- The "certain conditions" are the other tables the script multiplies in. Artifact count per drop is 1 (`death_items_count.ltx`, all difficulties). The level
  multiplier (`death_items_by_levels.ltx`) is 1 for the 0.5% tier ONLY on `l10_radar`, `l11_Pripyat`, `l12_stancia`, `l12_stancia_2`, `l12u_sarcofag`,
  `l12u_control_monolith` (and `stohe_selo`), and 0 on every earlier level (Escape to X16 and X10). Communities `military`, `zombied` and `monolith` have all
  artifacts at 0. Quest and `dont_spawn_loot` NPCs get no loot. (Mid-tier artifacts do drop at 1% on early levels in SoC; not changed here, see below.)

## What this mod had
`death_items_by_communities.ltx`, `death_items_by_levels.ltx` and `death_items_count.ltx` list every artifact (plain CoP ids and the `_soc` ids) at 0, and
the base xrMPE `death_manager.script` has the same integer roll. So no artifact could ever be created from a corpse, and the 0.5% value could not have worked
anyway. (World artifacts, stashes and quests are not touched: `soc_economy` / `no_mp_items` already turned the plain ids into SoC ones.)

## Change
- `scripts\death_manager.script` (copy of the base xrMPE one, nobody else ships it): the roll is now `math.random() * 100 < percent` (`roll_percent`), a real
  number, so 0.5 means 0.5%. For every value of 1 or more the result is the same as before (1% stays 1%, 100% stays always), except that values like
  `100 * 0.29 = 28.999...` no longer lose a percent. Other loot (ammo, food, medicine) is unchanged (checked: bread / medkit / bandage rates equal the stock script's).
- `configs\misc\death_items_by_communities.ltx`: the 12 `_soc` ids of the 0.5% tier are 0.005 in `[stalker]` (so also bandit, killer, ecolog, dolg, freedom,
  csky); `[army]`, `[zombied]`, `[monolith]` explicitly list them at 0 (SoC's military / zombied / monolith).
- `configs\misc\death_items_count.ltx`: the 12 ids are 1 in `[item_count_0]` (1 to 3 inherit it).
- `configs\misc\death_items_by_levels.ltx`: `[default]` keeps them at 0 (every early level, like SoC), and six sections `[coop_l09_radar]`, `[coop_l10_pripyat]`,
  `[coop_l11_stancia_1]`, `[coop_l11_stancia_2]`, `[coop_l11_control_monolith]`, `[coop_l11_sarcofag]` (the SoC late levels in this mod's names) set them to 1.
- Not changed on purpose: the mid-tier artifacts (1% and 1.5% in SoC) stay at 0 as in the mod; FOSTER asked for the last tier. To enable them, put the SoC value
  (0.01 / 0.015) in the three tables, nothing else is needed.

## Server authority, one roll per corpse
`create_release_item` runs only on the server (it calls `alife():create`), in `motivator_binder:death_callback` or, for a corpse that spawns dead, on the first
update. It starts with `se_obj.death_droped`, a flag of the server entity that `se_stalker` writes into the save, and sets it before rolling. So the corpse
content is rolled once, at death, by the server; the items are server objects with the corpse as parent and are replicated like every other loot item (the
same for every player, no per-player roll), and a save load never rolls again (offline test: a second call on the same corpse creates nothing).

## Host settings (works now, needs two table lines in host_settings)
`death_manager` reads `coop_host_cfg.num("corpse_artifacts", "chance_mult", 1)` (every artifact chance times this; 1 = SoC, 0 = off, 200 = 100%) and
`coop_host_cfg.bool("corpse_artifacts", "all_levels", false)` (true = also on the early levels and the Cordon), wrapped in `pcall` with the db default, so
a missing or broken `coop_host_cfg` changes nothing. Any key typed into `coop_settings.ltx` is read (`value_text` does not need a table entry), but the file
writer only writes keys of `build_groups()` in `patches\host_settings\...\coop_host_cfg.script`, which another agent was editing, so the two lines
`[corpse_artifacts] chance_mult` and `all_levels` still have to be added there for the host to find them in the generated file. The settings are read when
an actor spawns (`bind_stalker` calls `death_manager.init_drop_settings()`), i.e. at the next level start.
Test override (hooks only): `death_manager.corpse_art_test = { chance_mult = 200, all_levels = true }` then `death_manager.init_drop_settings()`;
`death_manager.corpse_art_stats = { deaths, rolls, drops }` counts the corpses and artifact rolls of this VM; the server log line `[CORPSEART] <npc> dropped <id>
(<percent> percent) level <name>` is printed for every artifact created.

## Offline check
`python tests\corpse_roll_test.py <mod>\source\gamedata.db0\configs\misc [<SoC reference folder>]` (needs `pip install lupa`; the second argument is a folder with
`config\misc\*.ltx` and `scripts\death_manager.script` extracted from the Steam SoC archives with `tools\xdb_soc.py`; env `XRMPE_DEATH_MANAGER=<path of the stock xrMPE script>`
adds the stock-mod check). It runs the real scripts with the real tables in a Lua 5.1 VM and a small engine mock, about 45 s. Result of the run (all PASS):
- SoC original: 40000 Radar stalker corpses, 0 drops of the 0.5% tier (the bug), af_medusa 1.08%.
- Stock mod: 0 artifacts on Radar.
- Patched, 40000 corpses on Radar: corpses with an artifact 2388 = 5.97% (expected 12 x 0.5% = 5.84%), each of the 12 ids 0.45% to 0.60% (battery 240 of 40000 = 0.60%),
  no other artifact id ever; bandit, killer, ecolog, dolg, freedom on Pripyat the same; army, zombied, monolith never; all 6 late levels drop (5.4% to 6.0%),
  all 12 other levels never; a second `create_release_item` on the same corpse creates nothing; `chance_mult 200` = every corpse holds all 12, `0` = none, `all_levels` works,
  host file `chance_mult 10` + `all_levels` gives the expected 46%; a throwing or missing `coop_host_cfg` gives the defaults; ordinary loot rates unchanged.
- `tools\check_conflicts.py` (no new conflict), `tools\check_lua_escapes.py` (no new line), `tools\luabal.py` (62 / 62), `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`: BUDGET OK.

## In-game test plan (one listen-host run, Cordon, not run yet)
```
python build.py <out>\zzz.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner corpseart -Mode listen -Clients 1 `
  -ExtraDir <out>\stage\gamedata -Hooks <repo>\patches\corpse_artifacts\tests\corpse_test.lua -SoakSeconds 400 -CompareTimeout 10 -ResultDir <dir>
python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix CA --require 10
```
The hook (`tests\corpse_test.lua`, uses `qa_lib`) sets the test override and kills spawned NPCs with `L.kill` (the normal death path):
A) chance 100%: 6 NPCs (stalker and bandit), each corpse must hold all 12 `_soc` ids exactly once (server children of the corpse), stats 6 / 72 / 72;
B) chance 10% each: 40 NPCs, drop rate 0.06 to 0.14, artifacts found = `corpse_art_stats.drops`;
C1) normal chance on Cordon: 30 NPCs, 0 rolls (Cordon is not an artifact level in SoC); C2) `all_levels` with the normal chance: 100 NPCs, 1200 rolls, 0 to 25 drops
(expected 6), artifacts found = drops. Also check `[CORPSEART]` lines in the log and, on the client, loot one corpse of phase A (inventory shows the artifacts, same
content as the server) and, optionally, save and load: the artifacts on the corpses stay the same and `[CORPSEART]` prints no new line.
Without the hook: console on the listen host, `death_manager.corpse_art_test = {chance_mult=200, all_levels=true}` plus `death_manager.init_drop_settings()` (script console),
kill a few stalkers, loot them; then remove the override and check on Radar or Pripyat that about 1 corpse in 17 carries one artifact.

## Files
`gamedata\scripts\death_manager.script`, `gamedata\configs\misc\death_items_by_communities.ltx`, `death_items_by_levels.ltx`, `death_items_count.ltx`;
tests: `tests\corpse_roll_test.py`, `tests\corpse_test.lua` (never shipped). Encoding kept (cp1251), CRLF kept.

## Кратко (RU)
Баг оригинальной ТЧ: шанс 0,5% (последний ценовой уровень, в т.ч. Батарейка) переводится в проценты как 100 * 0,005 = 0,5, а бросок `math.random(100) <= 0.5`
использует целое число от 1 до 100, поэтому условие никогда не выполняется (1,5% и 1% выпадают как 1%). Опечатки нет, это ошибка самого броска.
Условия в ТЧ: артефакты 0,5% могут быть только у сталкеров (stalker, bandit, killer, ecolog, dolg, freedom, но не military, zombied, monolith) и только на Радаре,
в Припяти и на ЧАЭС (на более ранних локациях множитель 0). Исправление: бросок `math.random() * 100 < percent`, 12 артефактов `_soc` с шансом 0,5% в таблицах
`death_items_*` и поздние локации в `death_items_by_levels.ltx`. Бросок один на труп, на сервере (`death_droped` сохраняется в сейве), одинаково для всех игроков.
Для хоста: `[corpse_artifacts] chance_mult` и `all_levels` в coop_settings.ltx (читаются, если строки вписать вручную; в таблицу host_settings их ещё надо добавить).
