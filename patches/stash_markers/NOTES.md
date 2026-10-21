# Stash markers on the PDA map (shared by the whole party)

Player request: "add markers for stashes/boxes" (dobavit metki dlya yashchikov).

## What the original SoC did
`scripts/treasure_manager.script` + `config/misc/treasure_manager.ltx` (ixray-team/ixray-1.0-stsoc, copies in `Downloads\SoC_COOP_features\stash_markers\refs`):
- 215 stashes. Each is an `inventory_box` with a numeric story id (`target = 5000...`), a name and a hint text, an item list that the manager spawns into the box, a community list and a `condlist` of weights.
- The player got the **info** in three ways: (1) first search of a dead stalker (`xr_motivator` use callback -> `treasure_manager:use(npc)`: 35 percent chance, then a weighted pick by npc rank / current level / community / quest infos), (2) a quest reward (`fox_pay_money` -> `esc_secret_truck_goods`), (3) "cool info" dialogue phrases with a `treasure =` key.
- Getting it: news tip "new stash location" and `level.map_add_object_spot_ser(box, "treasure", name + hint)`. Looting the last item (`take_item_from_box` callback, `is_inv_box_empty`) did `level.map_remove_object_spot`.
- SoC never marked ordinary breakable boxes or random caches. "Boxes" in the request means these stash boxes, so that is what is implemented. (An alternative, not done: mark every `inventory_box` or `physic_destroyable_object` with loot; that would flood the map and is not original behaviour.)

## What the add-on did before
- The stash boxes exist at the SoC positions (213 of 215, matched by level + position <= 0.3 m; only the two X16 ones have no SoC box) and are **already filled** by the add-on author through `[spawn]` custom data, with story ids equal to the box name (`esc_equipment_pipe_02_case`...).
- It ships the CoP `treasure_manager.script` with `secrets.ltx` (Zaton / Jupiter / Pripyat object names that do not exist on SoC levels). Nothing in the SoC part ever calls it, the MP actor binder never ticks or saves it, no dead-stalker hook, no dialogue, no `treasure =` data, no SoC text strings. So **no stash info was ever given and no spot was ever shown**. (The CoP manager itself is already shared: `map_add_object_spot_ser` + `map_sync_spot(..., SV_OBJECT_ID)`, and `game_sv` calls `treasure_manager.send_map_locations(gameID)` for joining clients. I reuse exactly those engine calls.)

## Co-op decision: shared knowledge, server decides
When any player gets a stash's info, **every player** gets the mark; it disappears for everybody when the stash is looted.
Why: players share the map, quests and loot; the stash contents are one pile in one box, so a private mark would make two players race to a box one of them cannot see, and the PDA is per-client in the engine anyway. The SoC single player semantics (one player = the whole knowledge) maps to "the party".
- State is two story flags per stash, saved with the game and synced to everybody including late joiners by the mod's own flag sync: `STASH_G_<ID>` (info given), `STASH_D_<ID>` (looted).
- Only the server rolls corpse searches, sets flags, tracks box contents, adds / removes the spot and `map_sync_spot`s it to all clients. Clients only display. `give()` and everything else return immediately when not `OnServer()`.
- Emptiness is tracked on the server: every item registers through `treasure_manager.register_item`, the script remembers which items have `parent_id == stash box`, and a 1 s tick checks that each still exists with that parent. When the last one is gone the stash becomes `D`, the spot is removed and the "stash emptied" tip is shown (also re-adds the spot after a level load for stashes that are given but not looted).
- A stash given while the party is on another level keeps the flag and its mark appears when the party gets to that level.

## Triggers (server side)
- First search of a dead stalker: `xr_motivator.motivator_binder.use_callback` is wrapped once at install (the add-on's own dead-body hook, which hands out "known flags"); the wrapper then rolls the SoC table (`stash_markers.on_corpse_use`). Weights come from SoC `condlist` (npc rank, level, community); quest-info gates (`+yan_kill_brain_done`, `+mil_miser_*`, `+bun_antenna_off`, `-bar_darklab_document_done`) read a story flag with the upper-cased info name, which does not exist in the add-on, so those ~14 stashes are only reachable through the API.
- `treasure_manager.get_treasure_manager():give_treasure("esc_secret_...")` and `stash_markers.give(id)` work for quest scripts (the Fox quest of SoC is not in the add-on).

## Files (install as loose files in gamedata\)
- `scripts/treasure_manager.script` - the add-on's file plus three guarded calls (register_item tracking, give_treasure for SoC ids, send_map_locations). Nobody else ships this file.
- `scripts/stash_markers.script` - the logic. `scripts/stash_markers_data.script` - generated: 213 stashes, box names, weights.
- `configs/text/rus/stash_markers.xml`, `configs/text/eng/stash_markers.xml` - `stash_hint_<id>` = name + hint, Russian (original SoC text) and English (written for this patch). The spot stores the string id, so each client shows its own language.
- `scripts/safe_box_data.script`, `configs/text/*/safe_box_markers.xml`, `configs/ui/map_spots_addon.xml`, `tools/gen_safe_boxes.py`, `tests/safe_box_markers_hooks.lua`: the safe-zone storage box marks (section below).
- `tools/gen_stash_markers.py` rebuilds the data and texts; `tests/stash_markers_hooks.lua` is the test-only in-game test.
No hooks are needed from other patches (no edits to `xr_conditions.dscript`, `xr_effects.dscript`, `bind_stalker.script`, `bind_physic_object.script`; the `stash_loot` patch is untouched and independent: it concerns breakable boxes).

## Tests
RESULTS_PLACEHOLDER

## Known limits
- The corpse hook only affects stalker binders created after the wrap (install happens at the first item registration of the level, before any stalker goes online).
- Quest-gated stashes (see above) are not handed out by corpses.
- Items put into a stash box by players are not tracked (only the original contents count).

## Safe-zone storage boxes (PDA marks from the start) - added 2026-10-21
Request (FOSTER): mark every storage box (the searchable `inventory_box`, "Search box (F)", like the blue metal box players keep their things in) in the safe
zones: Cordon (Sidorovich's bunker, rookie village campfire), the Garbage Duty checkpoint, the Bar, Yantar (Sakharov's bunker), the Army Warehouses (Freedom base).
These are not the treasure stashes above: they have no preset loot, are marked from the first second for everybody and the mark never goes away.

### Which boxes
Source: the add-on `level.spawn` of each level (`inventory_box` objects; the same names exist in `all.spawn`), rebuilt by `tools/gen_safe_boxes.py`
(`--list` prints the boxes and the skipped caches without writing). Zones: the no-weapon space restrictors the mod already uses (`sr_no_weapon_space_restrictor`,
box shape: 1 on Cordon, 2 in the Bar, 2 on Yantar); Cordon's rookie village, the Garbage Duty checkpoint and the Freedom base have no no-weapon restrictor, so they are a circle in x/z
(village: 30 m around `esc_campfire` -206.9 / -140.1; Duty checkpoint: 20 m around 40 / 238, next to `gar_duty_rush_space_restrictor` (30, 234) and `gar_smart_terrain_9`; Freedom base: 55 m around -30 / -2, which covers the trader's smart terrain 2, Max's smart terrain 11 and
the base's other smart terrains). A box counts when it carries no preset loot (no items in its `[spawn]` section); the loot caches inside the zones are left to the
stash markers above and are listed under "Skipped".

| Base | Level | Box (object name) | Position x, y, z |
|---|---|---|---|
| Sidorovich's bunker | coop_l01_escape | esc_equipment_box_01_case_0003 | -247.5, -24.8, -135.7 |
| Rookie village (campfire 5.5 m away) | coop_l01_escape | esc_equipment_box_01_case | -212.1, -20.0, -141.9 |
| Garbage, Duty checkpoint (north checkpoint toward the Bar; the blue trunk on a crate, FOSTER screenshot 28; `gar_duty_rush_space_restrictor` 20 m away) | coop_l02_garbage | gar_equipment_box_01_case_0002 | 48.2, 1.3, 241.3 |
| Bar, the 100 Rads bar (restrictor at 126.6, -3.7, 20.6) | coop_l05_bar | bar_equipment_box_01_case | 137.9, -4.8, 24.2 |
| Bar, Duty base (restrictor at 222.2, -1.7, 128.4) | coop_l05_bar | bar_equipment_box_02_case | 225.8, -4.3, 132.9 |
| Sakharov's bunker (2 restrictors at 28.7 / 29.0, -10 / -12, -272 / -279) | coop_l08_yantar | yan_equipment_box_01_case | 27.4, -11.7, -277.6 |
| Freedom base (trader area, 14 m from the trader's waypoint) | coop_l07_military | mil_equipment_box_01_case_0000 | -26.7, -5.5, -17.3 |
| Freedom base (Max's camp, campfire 6 m away) | coop_l07_military | mil_equipment_box_01_case_0004 | -57.5, -10.9, 32.2 |

8 boxes. Skipped (preset loot, inside the zones): Cordon `esc_equipment_box_01_case_0004` (vodka, Vyvert, antirad), `esc_equipment_instrument_case_01_case` (medkits),
`esc_equipment_rucksack_01_case_0000` (medkits, ammo, bandages); Garbage `gar_equipment_box_01_case_0004` (antirad, 5.5 m from the Duty box, a treasure stash of the SoC list), Freedom base `mil_equipment_box_01_case` (Freedom suits), `mil_equipment_box_01_case_0006` (ammo).
The Bar and Yantar boxes carry an empty `[spawn]` section and a story id, the others have no custom data at all (the `stash_loot` patch may roll one consumable into
those once, which does not affect the mark).

### How it works
- Data: `scripts/safe_box_data.script` (generated). Hints: `configs/text/{rus,eng}/safe_box_markers.xml`, string `safe_box_hint_<base>` = "Storage box" / "Ящик для вещей"
  (coloured title) + the base name, e.g. "Sidorovich's bunker" / "Бункер Сидоровича". The spot stores the string id, so every client shows its own language.
- Spot type `safe_box_location` (new, in `configs/ui/map_spots_addon.xml`, which this patch now ships: the mod's original content plus the new type). It uses SoC's
  personal-box icon `ui_common_player_box_spot` (the one `ui_pda2_actor_box_location` uses). It is a copy of that type without `scale_min="4"`: the SoC type is hidden on the
  PDA map until you zoom in, which would hide the marks at the normal zoom. No new texture.
- `stash_markers.on_register` (called from the shipped `treasure_manager.script` override for every server item) remembers the object id of each listed box.
  The 1 s server tick (`reconcile`, same tick as the stashes) puts the spot on the boxes of the CURRENT level with `level.map_add_object_spot_ser` (kept in the savegame)
  and sends it to every connected client with `level.map_sync_spot(..., SV_OBJECT_ID)`; a box is only handled when `level.name()` equals its level, so the Bar boxes get
  theirs when the party arrives. `send_map_locations(gameID)` (the engine calls it for every joining client through `treasure_manager`) re-sends them to that client.
- Never removed: nothing calls `map_remove_object_spot` for these boxes; opening, emptying or filling the box changes nothing. A missing spot (new level load) is added again,
  a present one is never added twice (`map_has_object_spot` guard).
- Server only (`OnServer()`); clients just display. No other file of another patch is touched.

### Test plan (single listen-host runs, `tests/safe_box_markers_hooks.lua`)
```
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner sbm -Mode listen -Clients 0 `
  -Hooks <repo>\patches\stash_markers\tests\safe_box_markers_hooks.lua -ExtraDir <stage>\gamedata -SoakSeconds 10 -CompareTimeout 10 -ResultDir <dir>
```
Add `-Cfg safe_travel=gar` (Duty checkpoint box; or `bar`, `yan`, `mil`) to travel from Cordon through the party vote (stalker.md section 4; the hook starts it 45 s in and runs the same checks again on the
new level). Listen host = server and the one client in one process. For a remote client use `-Mode dedicated -Clients 1` (the joining client checks `QA_SBOX_*` ids).
The hook prints to `qa_events.log` one line per box: `SAFEBOX <level> <name> id=<id> pos=x,y,z key=<base> hint=<text> server_spot=<n>`, then `SAFEBOX_COUNT level=.. boxes=N expected=N`,
and per client `SAFEBOX_CLIENT level=.. role=.. sees k/n`. Asserts (qa_assert.log): the data has 8 boxes; the server knows exactly the expected boxes of the level (Cordon 2, Garbage 1,
Bar 2, Yantar 1, Army Warehouses 2) and every one has a spot; the object positions match the table above (0.6 m); the spot count is exactly 1 per box 20 s later;
every client sees every spot (`level.map_has_object_spot(id, "safe_box_location")`).
Offline checks done: `check_conflicts.py` (nothing new), `check_lua_escapes.py` (nothing new), `luabal.py`, a mock-VM run of the script logic (add once per level, resync on
join, level switch), `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK. Not run in the game yet.
Open question for the first run: whether a client sees the spot of a box that is not online on its side yet (engine detail of `map_sync_spot`); the hook measures exactly that.

### Кратко по-русски
Ящики для вещей (обычные закрываемые `inventory_box` без предустановленного лута) в безопасных зонах отмечены на карте КПК с начала игры у всех игроков, в том числе у подключившихся
позже; метка не пропадает, когда ящик открыт или опустошён. Подсказка двуязычная: "Ящик для вещей" + название базы (Бункер Сидоровича, Лагерь новичков, Бар 100 рентген, Блокпост Долга (Свалка), Территория Долга,
Бункер Сахарова, База Свободы). Значок как у личного ящика в ТЧ (`ui_common_player_box_spot`), тип метки `safe_box_location` (копия `ui_pda2_actor_box_location` без `scale_min`,
иначе метка видна только при сильном увеличении карты). Ящики (8): Кордон: esc_equipment_box_01_case_0003 (бункер Сидоровича, -247.5 -24.8 -135.7), esc_equipment_box_01_case
(лагерь новичков, -212.1 -20.0 -141.9); Свалка: gar_equipment_box_01_case_0002 (блокпост Долга, 48.2 1.3 241.3); Бар: bar_equipment_box_01_case (137.9 -4.8 24.2), bar_equipment_box_02_case (Долг, 225.8 -4.3 132.9); Янтарь: yan_equipment_box_01_case
(27.4 -11.7 -277.6); Армейские склады: mil_equipment_box_01_case_0000 (-26.7 -5.5 -17.3), mil_equipment_box_01_case_0004 (-57.5 -10.9 32.2). Схроны с лутом внутри зон не
отмечаются (их метки выдаёт механизм схронов выше). Метки ставит только сервер раз в секунду для ящиков текущего уровня и рассылает всем клиентам (`map_sync_spot`), новым игрокам их
отправляет `send_map_locations`.
