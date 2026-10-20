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
- `tools/gen_stash_markers.py` rebuilds the data and texts; `tests/stash_markers_hooks.lua` is the test-only in-game test.
No hooks are needed from other patches (no edits to `xr_conditions.dscript`, `xr_effects.dscript`, `bind_stalker.script`, `bind_physic_object.script`; the `stash_loot` patch is untouched and independent: it concerns breakable boxes).

## Tests
RESULTS_PLACEHOLDER

## Known limits
- The corpse hook only affects stalker binders created after the wrap (install happens at the first item registration of the level, before any stalker goes online).
- Quest-gated stashes (see above) are not handed out by corpses.
- Items put into a stash box by players are not tracked (only the original contents count).
