# yantar_restore: Yantar / X16 content closer to original SoC

Requests from the maintainers, each checked against the original SoC logic (reference port `soc_ai_port`) and against the level data
that is still inside the add-on (`levels/coop_l08_*/level.spawn` and `level.game`, read from `coop.addon`).

Depends on `cutscenes_core` and `cutscenes_pkg_yantar` for the bus scene (item 3) and on the Scene Director for the script
`gamedata/scripts/coop_scn_yantar_restore.script` (found by the director's `coop_scn_*` file discovery).

## Status per item (PASS = proven in a real game run, dedicated harness unless noted)

| # | Item | SoC behaviour | Result |
|---|---|---|---|
| 1 | Bunker door and "may I use the room" dialog | SoC bunker doors open on their own (`door_trader.ltx`, locked=true closed=false); there is no door-asking dialog | Door `yan_door_trader_2_1` is permanently open: PASS (`active_section=ph_door@open`). Dialog `..._saharov_open_door_dialog` removed from Sakharov's `actor_dialog` list: verified by file only (the line is gone in the single shipped `character_desc_coop_l08_yantar.xml`, which lives in `patches/repeatable_quests`). The other locked door `yan_door_trader` (generic `scripts/door_trader.ltx`) was left alone. |
| 2 | Sakharov trade | `trade_ecolog.ltx` buys artifacts, all SoC ammo and grenade types, weapons, outfits, meds, food | The mod list already contained every SoC ammo caliber, weapon and artifact. Missing and added: bread, kolbasa, conserva, vodka, energy_drink, ecolog_outfit, monolit_outfit, soldier_outfit: PASS (`ini_file` check in game). CoP-only calibers (5.7x28, .50 AE, 7.62x25, 9x21, M397, PKM 100) are not in any SoC list and were NOT added. Another patch (`soc_economy`) edits the same file; keep both. |
| 3 | Kruglov goes with the player, emission at the bus | SoC: Kruglov accompanies the player to the three measurement sites (`YAN_KRUGLOV_AFTER_ACTOR`); the last site is the bus (177.9,-4.6,-99.5). The unused level paths `kruglov_3_3..3_6` run exactly along those sites | REVERTED for now (v1.4): the follow scheme (a `companion` section in `yan_smart_terrain_1_walker_kruglov.ltx`) and the reworded dialog line were removed because the walking was not proven and `no_meet` would block his quest dialogs. What was tried: after the preparation dialog Kruglov switches to `companion` (follow the nearest player, the same scheme as the Cordon Shustry escort) and goes home when `YAN_START_TAKE_MEASUREMENTS_3_QUEST_TASK_INFO` is set. Scheme switch: PASS. **Actually walking after the player: NOT proven** (run twice in listen mode and dedicated; Kruglov did not move at 22 m or 100 m, no script error in the log; cause not found, maybe the harness). The dialog line 3 ("I would go with you myself but...") was reworded in eng/rus so it fits. The emission/dream at the bus is the existing position scene `yantar_ghost_sleep` of `cutscenes_pkg_yantar` (10 m around 174.65,-7.80,-99.65). |
| 4 | Ghost's corpse | SoC `x16_stalker_ghost` lies dead in X16 with `lab_x16_documents`; `yan_ghost_pda` shows the tip "Ghost's audio recording" | Server script creates a dead stalker at the level's own `x16_space_restrictor_ghost_pda` (-75.06,5.59,-10.24) and the item `lab_x16_documents` next to it: PASS (object exists, not alive, documents item next to it, taking the documents sets `X16_GHOST_DOCS_TAKEN`). The SoC model `stalker_prizrak` and a custom character are not available (new character files crash the server because `system.ltx` lists the files), so the corpse is a random veteran stalker (`sim_default_stalker_3`). Floor: the engine snaps the body to the AI node at y=21.7, the SoC floor may differ. The PDA tip scene was not seen to play (untested). |
| 5 | Sakharov message and military helicopters after the lab | SoC `yan_saharov_message_3`: "radiation is off, we called a couple of military helicopters to clear the zombies, stay away, drop in at the bunker". The Sakharov reward dialog `installation_is_disabled` already exists in the mod | Scene `yan_heli` (server trigger: all 4 X16 lever flags and `X16_START_GET_OUT_OF_THE_LAB_TASK_INFO`) shows the message with Sakharov's icon: written, scene flow not seen in a finished run. **Helicopters are NOT in this patch.** The level has the flight paths (`heli_move_1..3`, `heli_look_1..3`, `heli_move_end_1,2`, `heli_stay_1..3`) but no helicopter object, and a helicopter created by script crashes the server (startup animation `$editor`). A fix needs two helicopter packets added to `level.spawn`; the attempt is in `wip_heli/` (not built into the patch, untested in game). |
| 6 | Yantar to Agroprom transition | SoC has none (confirmed by the maintainers). The mod's level graph equals SoC (Yantar links only Rostok and X16) | No change. |
| 7 | Military in the lab | SoC Agroprom underground soldiers are `agr_soldier_regular` (regular rank), the X18 scout is a spetsnaz lieutenant; both only use the generic `hello` dialog, there are no SoC story dialogs for them | Agroprom underground squads used `sim_default_military_0` (novice). Now `sim_default_military_1` (regular): PASS (all 8 members of `agru_smart_terrain_2/3_military_1_squad` checked in game). No dialogs added (SoC has none). X18's military (rank master) unchanged. |
| 8, 9 | Sarcophagus | see `patches/sarcophagus_count` | not this patch |

## Files
- `gamedata/configs/scripts/coop_l08_yantar/doors/yan_door_trader_2_1.ltx`
- `gamedata/configs/misc/trade/yan_smart_terrain_1_ecolog_saharov.ltx` (also edited by `soc_economy`)
- `gamedata/configs/misc/squad_descr_coop_l03_agroprom_underground.ltx`
- `gamedata/configs/creatures/spawn_sections_coop_l08_yantar.ltx` (Ghost section and `lab_x16_documents`)
- `gamedata/scripts/coop_scn_yantar_restore.script`, `gamedata/configs/text/{eng,rus}/st_coop_scn_yantar_restore.xml`
- `wip_heli/` helicopter level.spawn experiment (not shipped)
- Single copy rule: `character_desc_coop_l08_yantar.xml` is shipped only by `patches/repeatable_quests` (the open-door line is removed there).

## Tests
Hooks and logs are kept in the author's scratchpad (`yantar_story`); the harness is `tools/stalker_xrmpe/run_coop.ps1` (Cordon start, travel by guide flag).

## Кратко (RU)
Проверено в игре: дверь в бункере Сахарова открыта, трейд Сахарова дополнен продуктами и экипировкой из SoC, военные в Агропроме-подземелье теперь "регулярные", а не новички, труп Призрака с документами создаётся в X16. Круглов переключается на сопровождение, но реальное движение за игроком в тесте не подтверждено. Вертолёты и сообщение Сахарова: сообщение написано, вертолёты не включены (скрипт-вертолёт валит сервер; правка level.spawn лежит в wip_heli). Перехода Янтарь-Агропром в SoC нет, ничего не менялось. Саркофаг: см. patches/sarcophagus_count.
