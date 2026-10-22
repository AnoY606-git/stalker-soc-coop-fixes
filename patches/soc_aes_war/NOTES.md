# Power plant (CNPP-1): the fighting helicopters and the army BTR of the original SoC (v1.4.3)

Request (maintainer FOSTER, two lines): "Return the military BTR that drives in front of the Sarcophagus entrance" and "Helicopters that fly and attack the Monolith and the main
characters". Everything is made by script and config; **all.spawn and level.spawn are not touched** (saves keep working, the old section names of the helicopters are kept).
Offline work only: the game was not started. What is proven offline and what is not is listed at the end.

## What the original has (Steam SoC 1.0006, `l12_stancia` level.spawn, read with `soc_aes_military\tools\soc_spawn.py`)
| Object | Original |
|---|---|
| 10 helicopters `aes_helicopter*` | `heli_move` along `aes_heli_attack_*` paths, army "desant" waves, `combat_use_rocket = false` on the attack ones, `heli_set_enemy_actor` when the player stands in one of the zones `aes_actor_heli`, `_heli1`, `_heli2`, `_heli3`, death path at 30 % health. The helicopters of the original fight the player ONLY there; the Monolith RPG soldiers (`heli_hunter`) shoot at the helicopters |
| 5 BTRs `m_car` (`aes_btr`, `_0000`, `_0001`, `aes_m_car`, `aes_btr_0002`) | `ph_car` scheme: `path_walk`, turret `target = actor` (aims, no `auto_fire`) for four of them. The one in front of the Sarcophagus is `aes_btr_0002` at (365.8, -0.1, -150.3): `aes_btr_walk5` (366, -149) -> (367, -66) at 40 km/h, then `path_fire = aes_btr_look5` (the points (368, -8), (395, -17), (416, -37) at the entrance), `auto_fire`, created when the player passes `aes_actor_btr_ambush` (459.7, -120.3). It fires at the Monolith positions, not at the player |

## What the mod had
- 8 helicopters `aes_1_heli_attack_1..8` in all.spawn (custom data `cfg = scripts\coop_l11_stancia_1\aes_1_heli_attack_<n>.ltx`). Their files used the CoP "evacuation" routes `aes_1_helicopter_<n>_move_way_0`
  and had `combat_ignore_cond = true`, which is no key of the helicopter scheme (the key is `combat_ignore`), and nothing ever gave them an enemy (`heli_move` takes an enemy only from the
  logic key `enemy` or from the hit callback) - so they flew and never fired. Helicopter 1 pointed at `aes_1_helicopter_1_move_way_1`, a route that does not exist (engine abort 7 s after take-off).
- No `m_car` object at all (no vehicle in any level of the mod's all.spawn), and no path made for a vehicle.

## Does the engine support a BTR? (checked in the scripts, configs and archives)
Yes, as far as it can be read offline:
- class `SCRPTCAR` (section `m_car`, `script_binding = bind_car.init`) is registered for the server (`class_registrator`: `CCar` / `se_car.se_car`), `ph_car` is a loaded scheme
  (`modules.script`), its xrMPE version only attaches on the server (`add_to_binder: if OnClient() then return`) and aims with `getNearestActor`; xrMPE ships its own BTR with `ph_car` logic for the
  multiplayer map `mp_df_blokpost` (`blp_btr_logic.ltx`: `path_walk`, `auto_fire`, `target`).
- model `meshes\dynamics\vehicles\btr\veh_btr_script_u_01.ogf` + `textures\veh\veh_btr.dds` are in the add-on, the model config `models\vehicles\veh_btr_script_u_01.ltx` (car definition, wheels,
  `[mounted_weapon_definition]` with `wpn_section = stationary_mgun`) and the weapon `stationary_mgun` are in the xrMPE base configs. It is the script-car BTR model of Call of Pripyat (the `_script_` variant is the one made for `ph_car`).
- A section needs its own `visual` for `alife():create` (the stock `[m_car]` has none, a level.spawn object stores it), so the patch defines `[soc_aes_btr]` with the model and the keys of `[m_car]`.
Not provable offline: that the xrMPE server really builds and replicates a SCRPTCAR that was created by `alife():create` instead of coming from all.spawn (the BTR of `mp_df_blokpost` is the only
evidence). That is the reason for the switch below and for the test hook.

## What was done
### 1. Helicopters (`configs\scripts\coop_l11_stancia_1\aes_1_heli_attack_1..8.ltx`, `scripts\coop_soc_aes_war.script`)
No new helicopters are created (a script-created helicopter would need a section, a logic file and would stack on a reload; the 8 existing ones are exactly what the original had left of its 10).
- Logic files rewritten (made by `tools\gen_configs.py`): the sections `heli_move@idle / fly_ready / fly_0 / fly_1` of the old files stay (a save stores the active section by name), every route exists,
  rockets are off (`use_rocket = false`, the original attack helicopters had no rockets either), speed 90 km/h on the patrol (was 300), the take-off is staggered (5 s apart, 5 to 35 s), helicopter 1 flies
  the loop of helicopter 7 (8 s after it) instead of the missing route. They leave the yard when the mod's own flag `PRI_START_GO_TO_CNPP_QUEST_TASK_INFO` OR the new flag `SOC_AESW_GO` is set.
- `SOC_AESW_GO` (server): a living player on the SoC `actor_ready` line (926, -170.6) or already west of x 905 (the SoC info `aes_desant_go`).
- Enemies, once a second, server only (`heli_step`): only helicopters within 350 m of a living player work, the 3 nearest are armed. A helicopter takes
  1. a player, only while he stands in one of the four SoC helicopter zones (positions and boxes equal the SoC restrictors, checked by `tools\check_war_chain.py`), within 300 m and visible to the
     helicopter; at most 2 helicopters hunt players at once;
  2. otherwise the nearest Monolith soldier (`character_community() == "monolith"`, alive) within 250 m that it can see.
  It calls `heli:SetEnemy(obj)` (the call `heli_fire` uses), sets the machine gun on and the rockets off, and repeats it every 4 s (a section switch clears the enemy). Nothing else of the helicopter code
  is changed; a hit by a player still makes it fire back (`bind_heli`).
- A helicopter that is shot down (it leaves `db.heli` through `bind_heli.heli_die` while `m_dead` is true) is counted: story flags `SOC_AESW_DOWN_1..3` (first, second, third). Patch soc_aes_military
  plays the SoC lines `aes_choper_down_1..3` for them (radio trigger on a flag). A helicopter that only went offline is not counted.
- Count, stacking, soft locks: 8 existing objects, none created or released by the script; a reload finds them as they were. Players are attacked only in the four zones and by at most two helicopters;
  the machine gun is the only weapon; nothing blocks a quest or a door.
### 2. BTR (`[soc_aes_btr]` in `spawn_sections_coop_l11_control_monolith.ltx`, `soc_aes_btr.ltx`, the same script)
- ONE BTR (SoC `aes_btr_0002`), created once with `alife():create("soc_aes_btr", ...)` when a living player comes within 450 m of its start, at the point 9 of the army assault route of smart
  terrain 5 (`aes_1_smart_terrain_5_walker_army_ordinary_7_walk`): (412.2, 0, -127.5), level vertex and game vertex are the ones stored in the route. No patrol path can be added without all.spawn, so the
  BTR uses the last part of an existing route: `ph_car` starts at the nearest point (point 9), drives points 10 and 11 and stops at (374.8, 0, -61.6), 62 m before the Sarcophagus entrance and 9 m from
  the SoC end point (367, -66). The SoC route (366, -149) -> (367, -66) is a straight line on the same road; the mod's route is the level maker's army road, the BTR starts 51 m east of the SoC start.
  The BTR does not block the entrance (the entrance and the SoC "found" sphere are 62 m further).
- Once only: the flag `SOC_AESW_BTR_MADE` is set after the create, the section has a `story_id`, an existing entity of the section (lost registry entry or lost flag) is found by one scan of the server
  objects per Lua VM and reused. A destroyed BTR stays destroyed (like the SoC one). At most 3 create attempts, 5 s apart; a missing route or section skips it.
- The gun is run by the script, not by `ph_car` (the SoC `target = actor` aims at the player; the task says the BTR is hostile to the Monolith and neutral to the players): once a second the nearest
  Monolith soldier within 90 m that `car:IsObjectVisible` gets `SetParam(eWpnDesiredPos, pos)` + `Action(eWpnFire, 1)`, otherwise `Action(eWpnFire, 0)`. Never a player, never the army. The `ph_car`
  logic has no `target`/`path_fire`, so it does not touch the gun and the car is not "destroyed" at the end of its route (`state_cannon` stays none).
- It is a server object with logic on the server only; the clients get the car from the network like any other object.
### 3. Switches and radio
- `configs\misc\coop_aes_war.ltx`: `[soc_aes_war] helicopters = true`, `btr = true`. Set `btr = false` if the BTR misbehaves in the game (nothing else depends on it).
- Radio: patch soc_aes_military triggers `DN1..DN3` on the flags (see its NOTES, v1.4.3).

## Files
`gamedata\scripts\coop_soc_aes_war.script`, `coop_scn_soc_aes_war.script` (starts the tick like every `coop_scn_*`); `gamedata\configs\scripts\coop_l11_stancia_1\aes_1_heli_attack_1..8.ltx`, `soc_aes_btr.ltx`;
`gamedata\configs\creatures\spawn_sections_coop_l11_control_monolith.ltx` (the mod's file byte for byte + `[soc_aes_btr]`; no other patch ships it); `gamedata\configs\misc\coop_aes_war.ltx`.
Tools: `tools\gen_configs.py` (writes the config files), `tools\check_war_chain.py` (static proof); tests: `tests\mock_test.py` (68 checks), `tests\soc_aes_war_hooks.lua` (game test).
Size: about 16 KB, no model, no texture, no sound (the BTR model and the sound are in the add-on and the base game).

## Offline checks done
- `python patches\soc_aes_war\tests\mock_test.py`: 68 PASS (real script in a Lua 5.1 VM with an engine mock): nothing off CNPP-1; go flag; Monolith targets (nearest visible, range 250, not zombified, not invisible);
  players only inside the four zones and at most 2 hunters; sleep beyond 350 m; at most 3 armed; target repeated after 4 s; rockets off; shot-down counter 1..3 in order, a helicopter that only went offline
  is not counted; BTR created once (reload, registry loss, lost flag, destroyed BTR, missing route/section, create raising/returning nil, 3 tries), only within 450 m; gun fires at the nearest visible
  Monolith soldier within 90 m, not beyond, not at players, falls back to 50 m when the visibility call fails, no weapon = no error; both switches.
- `python patches\soc_aes_war\tools\check_war_chain.py "<mod source>" --soc-level-spawn <SoC l12_stancia level.spawn> --base-cfg <xrMPE base configs> --addon-names <add-on file list>`: 0 problems (8 helicopters
  in all.spawn with the right `cfg`, every `path_move` is a patrol path, every switched section exists, old section names kept, no rockets; BTR route and vertices, `[soc_aes_btr]` repeats every key of `[m_car]`,
  model, texture, model config and `stationary_mgun` exist; the four zones equal the SoC restrictors; no other patch ships these files).
- `tools\luabal.py`, `tools\check_lua_escapes.py` (nothing new), `tools\check_conflicts.py` (no new overlap), `tools\check_ogf_includes.py`; `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry`: BUDGET OK.

## Not proven (needs the game; one listen run with the hook below)
1. That a helicopter really fires at the enemy set by `SetEnemy` from this script on the xrMPE server and that the bullets hurt (the call is the one `heli_fire` makes; the damage values are the stock `helicopter.ltx`).
2. That `alife():create("soc_aes_btr")` produces a working car in xrMPE (visual from the section, binder, replication to clients, driving by `ph_car`, the gun). If it does not, set `btr = false`.
3. That the level maker's army road is drivable for a BTR from point 9 to point 11 (it can get stuck; `ph_car` then stops it, nothing else happens).
4. Whether the 8 helicopters are always online (a CSE_ALifeHelicopter normally never switches offline). If they were offline in their yard (465 m from the start) nothing would fly; the hook logs it.

## Game test (not run)
```
python build.py <out>\zzz.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner aeswar `
  -DbFile <out>\zzz.db -Hooks <repo>\patches\soc_aes_war\tests\soc_aes_war_hooks.lua -Cfg no_respawn=1 -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir>
python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix AESW
```
The hook travels to CNPP-1, checks no go flag at the arrival, the go flag on the `actor_ready` line, that a helicopter leaves its yard, that a helicopter gets an enemy in the first SoC zone (logged, not
asserted: it needs a target in view), shoots one down by script (flag `SOC_AESW_DOWN_1` and the radio line on host and client), then walks the party to 400 m from the BTR spot and asserts: the BTR is
created, online with its binder and a gun, driving (moved more than 5 m in 25 s), and the client sees the object. Screenshots `aesw_zone1`, `aesw_btr`.

## Кратко по-русски
Патч `soc_aes_war` (ЧАЭС-1), всё скриптом и конфигами, без правок all.spawn и level.spawn. Вертолёты: 8 вертолётов уровня (были, но только летали) получили новые файлы логики (патруль по маршрутам,
только пулемёт, вылет по очереди) и скрипт, который раз в секунду даёт им цель: ближайший видимый солдат Монолита в 250 м; игрока вертолёт атакует только в четырёх оригинальных зонах
(`aes_actor_heli*`), не больше двух вертолётов на игроков. Не больше трёх вертолётов «включены» одновременно и только в 350 м от игрока. Сбитый вертолёт ставит флаг `SOC_AESW_DOWN_1..3`
(радио `aes_choper_down_*`). БТР: движок его поддерживает (класс SCRPTCAR, схема `ph_car`, модель и пулемёт есть в аддоне и базе), один БТР создаётся один раз (`alife():create`, секция `soc_aes_btr`)
на дороге армии и едет к входу в Саркофаг, останавливается за 62 м до него; пулемёт скрипт наводит на видимых солдат Монолита в 90 м, по игрокам и армии не стреляет. Выключатели: `configs\misc\coop_aes_war.ltx`.
Не проверено в игре: стрельба вертолётов по цели из скрипта, создание БТР в xrMPE (если не работает: `btr = false`), проходимость дороги. Тест: `tests\soc_aes_war_hooks.lua`.
