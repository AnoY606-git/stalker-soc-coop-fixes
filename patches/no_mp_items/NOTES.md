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

## Artifact icons (2026-10-21)
Report: "Stone Flower from the Cordon elevator has the Jellyfish icon". Checked with `tools\artifact_icons.py` (every artifact section,
inheritance resolved, inv_name + grid cell, the cell compared pixel by pixel with the Steam SoC `ui_icon_equipment.dds`):
- `af_cristall_flower` / `_soc` (24,0) show exactly the SoC Stone Flower icon (SoC 11,4, orange stone). The Jellyfish is a different, brown
  icon (9,4, same in the mod and SoC). The CoP Stone Flower (blue holes) stays unused at 11,4 of the mod texture. No flower fix needed;
  the two icons only look alike in outline.
- One real mismatch found and fixed: `af_dummy_battery_soc` (name "Battery") used the icon of SoC `af_dummy_dummy` (vase, 32,0) instead of
  SoC `af_dummy_battery` (lattice). The mod texture already holds the lattice at 36,1: `artefacts_soc.ltx` (copy of the mod file, only
  that cell changed) now uses it; `af_dummy_battery` inherits it. The world model (`artefact_pustishka1.ogf`) is unchanged on purpose.
- Test: `tests\artifact_icons_hook.lua` (reads inv_grid of the sections from system_ini and gives them to the player).
  run: `powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Owner ai -Clients 1 -ExtraDir <stage>\gamedata -Hooks <repo>\patches\no_mp_items\tests\artifact_icons_hook.lua -SoakSeconds 60 -ResultDir <dir>`
