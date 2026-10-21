# Breakable boxes (wooden boxes, metal cases) breaking empty

## Root cause
Original SoC fills breakable boxes through `physic_destroyable_object` entries in all.spawn whose custom_data has a `[drop_box]` section (`items = ...` or `community = ...`). `bind_physic_object.script` binds them and, on the death callback, `xr_box.ph_item_box:spawn_items()` creates the loot (the mod's copy of both scripts is the same code as SoC's, plus an `OnServer()` guard). Three things break that in Shadow of COOP:

1. **The add-on spawn lost the data.** SoC 1.0006 has 375 `[drop_box]` boxes (359 on levels the add-on has). The add-on's level.spawn / all.spawn keep `[drop_box]` on only 76 of its 1210 boxes (Cordon 28, Bar 10, Rostok 20, Pripyat 10, Control Monolith 8). The other levels (Garbage, Agroprom, Dark Valley, X18, Military, Yantar, Radar, X10, CNPP...) have none at all.
2. **Community boxes roll against zero tables.** `ph_box_items_by_levels.ltx` picks the level multiplier section by `level.name()`. SoC has `[l01_escape]`, `[l02_garbage]`... with non-zero multipliers and a `[default]` of all zero. The add-on levels are called `coop_l01_escape` etc., so every box falls into the add-on's `[default]` (only food, 1 item, no ammo/meds/artifacts). Boxes with `community = ...` (47 of the 76) therefore drop next to nothing. Only boxes with an explicit `items =` line (29, all on Cordon/Rostok) dropped what SoC drops.
3. **Boxes with `[drop_box]` but no `[logic]` are never bound.** The mod's `bind_physic_object.init` returns when there is no `logic` section; SoC also binds when `drop_box` exists. The 8 Control Monolith boxes have exactly that, so they can never drop anything.

Also the add-on renamed the box objects (`gar_surprise_box_0001` became `gar_box_wood_01_0000`, only Bar/Rostok/Stancia-1 kept SoC names), so boxes cannot be matched by name; positions match exactly.

## Counts (add-on level.spawn, physic_destroyable_object = breakable boxes/decor)
| level | objects | SoC with loot | matched in add-on | add-on has [drop_box] |
|---|---|---|---|---|
| coop_l01_escape | 120 | 54 | 48 | 28 |
| coop_l02_garbage | 43 | 17 | 17 | 0 |
| coop_l03_agroprom | 69 | 23 | 23 | 0 |
| coop_l03_agroprom_underground | 27 | 10 | 4 | 0 |
| coop_l04_darkvalley | 81 | 26 | 26 | 0 |
| coop_l04_x18 | 183 | 16 | 15 | 0 |
| coop_l05_bar | 18 | 10 | 10 | 10 |
| coop_l06_rostok | 24 | 14 | 14 | 20 |
| coop_l07_military | 150 | 40 | 40 | 0 |
| coop_l08_x16 | 66 | 0 | 0 | 0 |
| coop_l08_yantar | 69 | 21 | 21 | 0 |
| coop_l09_radar | 104 | 30 | 30 | 0 |
| coop_l09_x10 | 100 | 27 | 27 | 0 |
| coop_l10_pripyat | 27 | 10 | 10 | 10 |
| coop_l11_stancia_1 | 7 | 6 | 6 | 0 |
| coop_l11_stancia_2 | 31 | 36 | 0 | 0 |
| coop_l11_control_monolith | 49 | 8 | 8 | 8 |
| coop_l11_sarcofag | 42 | 11 | 7 | 0 |
| **total** | **1210** | **359** | **306** | **76** |

"SoC with loot" counts the original SoC boxes of the matching level (the SoC brain lab, 16 boxes, has no add-on level). 306 of 359 exist in the add-on at the same position (within 0.3 m) and get their SoC loot now; the other 53 (Cordon army checkpoint 6, Agroprom underground 6, X18 1, CNPP-2 36, Sarcophagus 4) do not exist in the add-on's level (different layout, boxes removed). Additionally the 12 add-on boxes that carry their own `[drop_box]` but have no SoC counterpart (Cordon 6, Rostok 6) now also roll with the SoC tables.

Before: effectively 29 boxes (explicit item lists) dropped loot, 47 dropped almost nothing, 8 nothing. After: 306 + 12 + the mod-only ones = 318+ boxes drop SoC loot.

## What changed
- `gamedata/scripts/stash_loot.script` (new): server-only drop handler and a small binder for boxes. Same rolls as SoC `xr_box` (explicit lists create `count` of each item; communities roll per item with the SoC percentages, SoC level multipliers and `item_count_<difficulty>` min/max; ammo through `create_ammo`), same +-0.3 m / +0.3..0.5 m scatter. Loot is created only when `OnServer()`, once per box id (`spawned[]`), so players never get duplicate or per-player loot; clients just see the replicated items.
- `gamedata/scripts/stash_loot_data.script` (new, generated): SoC tables flattened for the 17 coop levels plus `boxes[level][add-on object name]`. Rebuild: `python patches/stash_loot/tools/gen_stash_loot.py` (downloads the SoC 1.0006 spawn dumps and ph_box configs from github.com/Roman-n/XRay-1.0006 on first run; reads the add-on level.spawn with tools/xdb.py; checks every item against the mod's configs).
- `gamedata/scripts/bind_physic_object.script`: the mod's file (xrmpe_patch) plus two lines at the top of `init()`: `if stash_loot.try_bind(obj) then return end`. Boxes with a real `[logic]` scheme keep the generic binder. Boxes that carry their own `[drop_box]` custom_data and are not in the table also go through `stash_loot` (this fixes the unbound Control Monolith boxes and the zero level multiplier).
- Item mapping: artifacts use the `_soc` twin (as the mod's own loot tables do); `killer_outfit` -> `merc_outfit` and `wpn_eagle_m1` -> `wpn_desert_eagle_m1` (renamed in the add-on). All other SoC sections exist unchanged. No other patch file is touched; no .dscript is changed.

Source of "original SoC": github.com/Roman-n/XRay-1.0006 (unpacked 1.0006 all.spawn dumps and config). It matches the ixray-team/ixray-1.0-stsoc `ph_box_*` config and `xr_box` / `bind_physic_object` scripts exactly. The Steam install's SoC .db archives use a compression the CoP reader cannot read, so they were not used.

## Multiplayer risks
- The drop happens in the object's death callback on the server (`OnServer()`); other machines run the same binder but create nothing. A box broken by a remote client relies on the hit being processed on the server, as for the existing explicit-item boxes (only a local listen server was tested).
- Not savegame related (`net_save_relevant` false, the binder keeps no state), so loading does not respawn loot; a box that was already broken is gone.
- Random community rolls differ per break, like SoC.

## Boxes without SoC data (FOSTER's rule) - added 2026-10-21
FOSTER's report: no box in the whole game has loot, wooden or metal. Suggested rule: consumables, 30 percent in wooden boxes, 50 percent in metal boxes. Owner rule: SoC first. So the order is: (1) the box exists in SoC with loot data -> SoC data (above); (2) the box has no SoC loot data -> FOSTER's rule below.

Which boxes: `gamedata/scripts/stash_loot_kinds.script` (generated by `tools/gen_box_kinds.py` from the add-on level.spawn): `physic_destroyable_object` boxes that are not in `stash_loot_data.boxes`, have no own `[drop_box]`, no `[logic]` and no `[story_object]`. The visual decides: wooden = `box_wood_01/02/tara`, `box_1a/1b`; metal = `box_metall_01`, `box_lab_03`. Plus plain `inventory_box` objects with no custom data at all (the stash boxes carry `[spawn]` and are filled by the add-on author; story boxes are left alone). Totals: 444 wooden, 70 metal, 17 inventory boxes (Cordon: 34 wooden, 5 inventory, 0 metal). Most metal boxes already had SoC data (157 of them are in the SoC table), so the metal rule only reaches 70 boxes on X18, X16, X10 and the Sarcophagus.
Everything is in `gamedata/configs/misc/box_loot.ltx`:
- `[settings]` `enabled`, `fallback_breakable`, `fallback_inventory`, `wood_chance = 30`, `metal_chance = 50`, `inventory_chance = 50`, `items_per_roll = 1`, `ammo_min/ammo_max`.
- `[consumables]` weights: bread, kolbasa, conserva, vodka, bandage, medkit, antirad and `ammo` (= one ammo type from the level tier list). Unknown sections are ignored.
- `[tier_<level>]` ammo types per level (9x18 + 12x70 on Cordon, 5.45/5.56/9x19 mid game, AP and 7.62x54 late).
How it works (all in `stash_loot.script`, server only): a wooden/metal box rolls once when it breaks (`spawned[id]` guard, so a second break/hit creates nothing). An inventory box rolls once when it first comes online: the item is created inside the box (`alife():create(..., box_id)`) and the roll is remembered in the shared story flag `SBOX_<NAME>`, so it is never refilled after a reload, level change or second player joining. Clients only see the replicated items; nothing is rolled per player.

## Test (Cordon, `tests/box_loot_test.lua`, `tools/stalker_xrmpe/run_coop.ps1`)
Runs: dedicated server + 2 real clients (first version of the hook), dedicated + 1 client, and listen server (host is the player). The hook breaks boxes by a server `hit()` and counts what appears.
- Dry statistics, 3000 `plan()` rolls per kind: wooden 892-943 wins (30 percent, 99.9 percent band 812-988), metal 1469-1470 (50 percent, band 1404-1596), inventory 1478-1497; every pick is an existing section, ammo only from the Cordon tier, every consumable of the list appears. PASS in every run.
- All 34 fallback wooden boxes on Cordon broken by a server hit: the death callback fired for 33 of 34 (the `box_wood_tara` box does not break from the test hit); wins 7/33, 10/33, 11/33, 14/33 over four runs (30 percent expected, band 0-20); new loose items next to the boxes equal exactly the rolled drops (e.g. 15 = 15, 7 = 7), `ammo*N` stacks split by box size. A hit with a big impulse knocked neighbouring SoC boxes over (extra SoC loot), so the test uses impulse 5, after which the count is exact.
- Metal rule (same handler, `on_death(obj, {k = "m"})` on 60 intact destroyable objects, because Cordon has no metal box without SoC data): wins 41/60 and 28/60 (50 percent, band 16-44); created objects equal the rolled ones (48 = 48, 32 = 32).
- SoC-data boxes (explicit lists and communities) dropped exactly their SoC list when broken in the engine (e.g. `antirad,bandage,bandage,bandage`, `bandage,bandage`, `af_cristall_flower_soc`); this was untested before.
- Inventory boxes (kind "i", 2 online on Cordon): each rolled once (flag `SBOX_<NAME>` set), content equals the roll (0, 1 or 3 objects), a second fill call changes nothing. (Found and fixed in the test: `give_flag` upper-cases the name, `has_flag` does not, so the flag name is upper-cased in the script.)
- Second death call / second hit of the same boxes rolls no box twice (new rolls 1 = the one box whose first callback never fired).
- Two real clients (dedicated server, first hook version): both clients saw the same number of new loose items as the server created, i.e. no per-player duplicate. The id-based version (every server-created id seen once on the client, nothing created locally) passed with 1 client; the later 2-client runs were lost to out-of-memory crashes of client B, because other test lanes used the PC at the same time.
- Boot: Cordon loaded with the patch in all runs, no script error; X18 also booted (the player starts far from the boxes there, so no box was online to break).
- Limits of the evidence: the boxes were broken by a server-side hit, not by a player bullet or grenade; item drops were not counted for a box broken by a remote client's shot.

## Кратко по-русски
Ящики теперь не пустые. Если ящик есть в оригинальной SoC и у него там был лут, то выпадает оригинальный лут (таблицы SoC, 306 ящиков). Для остальных ящиков работает правило FOSTER: деревянный ящик при разбивании с шансом 30 процентов даёт один расходник (хлеб, колбаса, тушёнка, водка, бинт, аптечка, антирад) или патроны по уровню, металлический с шансом 50 процентов, обычный закрытый ящик (inventory_box) один раз, на сервере, с шансом 50 процентов; повторно не заполняется после загрузки. Шансы, веса предметов и патроны по уровням настраиваются в `configs\miscox_loot.ltx`. Всё создаётся только на сервере, один бросок на ящик, дублей для второго игрока нет. Проверено на Кордоне: 33 из 34 ящиков разбились, доля выпадений около 30 процентов (металлических 50), предметы появились ровно там, где выпал бросок.
