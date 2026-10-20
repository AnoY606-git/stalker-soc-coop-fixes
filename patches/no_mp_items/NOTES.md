# No MP items - notes

## Problem
xrMPE keeps separate `mp_*` copies of items for its PvP modes. Co-op must use the normal (single-player) items only:
for example MP ammo does not fit the normal AK-74 (maintainer report). Places where co-op still handed out MP items:
- every player spawned with `mp_wpn_knife`, `mp_device_torch`, `mp_wpn_binoc` (`configs\mp\cooperative_game.ltx`, `default_items`),
- quick slots 1 and 3 defaulted to `mp_medkit` / `mp_antirad` (`configs\creatures\actor.ltx`),
- a generic task reward was `mp_wpn_toz34` (`configs\alife.ltx`, `[reward_for_genric_task]`),
- anomalies could spawn the MP-only artifacts `mp_af_electra_flash`, `mp_af_cta_green`, `mp_af_cta_blue` (`configs\misc\artefacts.ltx`).

## Fix
- `default_items = wpn_knife, device_torch, wpn_binoc`. The engine only hands out items that have an entry in the game
  type's cost table, so the three items were added to `[cooperative_base_cost]` with cost 0. This file is shipped by
  `patches\marked_one` (one patch per file), the edit is there.
- Quick items: `medkit`, `antirad`. This file is shipped by `patches\no_grenade_tinnitus`, the edit is there.
- `gamedata\configs\alife.ltx`: reward `wpn_toz34`.
- `gamedata\configs\misc\artefacts.ltx`: the three MP artifact lines are commented out.
Not changed: the buy-menu groups in cooperative_game.ltx (co-op has no buy menu) and the MP item definitions themselves.

## Test (Cordon, dedicated server + 1 client)
Stock: the spawned player carries `mp_wpn_knife, mp_device_torch, mp_wpn_binoc`. Patched: `wpn_knife, device_torch,
wpn_binoc`, no `mp_*` item (PASS). Without the cost entries the player got no knife, torch or binoculars at all.

## Кратко (RU)
В коопе больше не выдаются МП-предметы: стартовые нож, фонарик и бинокль теперь обычные (не mp_), быстрые слоты по умолчанию обычная аптечка и антирад, награда за задание обычная ТОЗ-34, МП-артефакты больше не появляются в аномалиях.
