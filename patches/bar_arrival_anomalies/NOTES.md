# Bar: no anomalies where players arrive (coop_l05_bar)

FOSTER (screenshot, Garbage -> Bar): "In the Bar, right in front of the level transition, remove the anomaly, it stands too close to the spawn."

## What it was
The glow ahead of the arrival point is the stock SoC gravitational mine `level_prefix_zone_mine_gravitational_strong` (eid 2506,
position 354.7, 9.3, -178.0), 12.1 m from the Garbage -> Bar arrival point (361.9, 11.0, -187.6); bearing 323 degrees, the screenshot's
compass reads 320. It is not an addition of the mod: the Bar's `all.spawn` and `level.spawn` have the same 60 anomaly zones as the SoC Bar
(`level_prefix_*` and `bar_zone_*` names). No script of the mod spawns anomalies (grep over scripts and configs, nothing references the names).
`campfire` / `camp_zone` objects are not anomalies and stay.

## Arrival points of the Bar
Read from the `dest_position` of the level changers in `spawns\all.spawn` and from the Bar's `level.game`:

| Route | Point |
|---|---|
| Garbage -> Bar (`gar_bar_level_changer`) | 361.9, 11.0, -187.6 |
| Rostok -> Bar (`ros_bar_level_changer`) | 55.3, 0.0, 140.0 |
| Wild Territory -> Bar (`mil_bar_level_changer`) | 57.1, 0.0, 169.4 |
| Cordon guide / party vote -> Bar (`6_esc_bar_guide_level_changer`) | 169.4, 0.0, 65.8 |
| co-op spawn points (team 4) and neutral points of `level.game` | 105.0, -15.8, -8.4 to -12.6 and 108.5, -15.8, -9.8 to -12.6 (no anomaly within 45 m) |

## Removed: ONE zone (v1.4.2)
Decision of FOSTER after the first version ("return all but one"): only his own anomaly stays removed.

| Section | Name | Position | Distance to the arrival |
|---|---|---|---|
| zone_mine_gravitational_strong | level_prefix_zone_mine_gravitational_strong (FOSTER's) | 354.7, 9.3, -178.0 | 12.1 m (Garbage -> Bar) |

The first version (v1.4.1) had removed every `zone_*` object within 30 m of an arrival point, 10 zones. The other nine are back, exactly as in the
original SoC Bar (`all.spawn` and `level.spawn`, the same chunks of the mod's own original files):

| Name | Position | Distance to an arrival |
|---|---|---|
| bar_zone_field_radioactive_strong_0003 | 364.3, 10.8, -180.4 | 7.6 m (Garbage) |
| bar_zone_field_radioactive_strong_0004 | 347.2, 9.6, -180.6 | 16.3 m (Garbage) |
| level_prefix_zone_mine_gravitational_strong_0000 | 378.1, 14.1, -202.6 | 22.3 m (Garbage) |
| level_prefix_zone_mine_gravitational_strong_0011 | 52.5, 0.0, 164.2 | 6.9 m (Wild Territory) |
| level_prefix_zone_mine_gravitational_strong_0014 | 70.7, 0.0, 164.2 | 14.5 m (Wild Territory) |
| level_prefix_zone_mine_gravitational_weak | 48.6, -0.1, 183.3 | 16.3 m (Wild Territory) |
| level_prefix_zone_mine_electric_strong_0010 | 58.4, -0.5, 194.9 | 25.5 m (Wild Territory) |
| level_prefix_zone_mine_electric_strong_0011 | 56.2, -0.5, 198.7 | 29.3 m (Wild Territory) |
| bar_zone_field_radioactive_strong_0016 | 152.3, 0.0, 56.3 | 19.5 m (Cordon guide) |

(An intermediate plan, "keep removed only what is closer than 15 m", was dropped when FOSTER answered.) The artifacts these zones spawn work as in SoC again.

## How
- `tools\strip_bar_anomalies.py`: in-place step on an `all.spawn` (same pattern as `no_tech_parts	ools\strip_spawn.py`: selects by section, name and
  position, never by id, renumbers the spawn ids contiguously, atomic write, refuses when the file changed meanwhile, idempotent, any order).
  It drops FOSTER's zone only. `--ref <original all.spawn>` also RE-ADDS every Bar zone of the original that the target lacks (each one goes right after
  the entity that preceded it in the original, so the original order is kept), which is how the nine were brought back into files that had lost them.
  `--check [--ref ...]` (exit 1 when FOSTER's zone is present or a zone is missing), `--report` (every Bar zone, marks the one removed),
  `--level-spawn <in> <out>` for the Bar's `level.spawn`.
- The original `all.spawn` is in `Shadow of COOP 8.0\addon_unpacked` (`python tools\xdb.py <addon_unpacked> extract <dir> "spawns\all.spawn"`, file
  `<dir>\gamedata.db1\spawns\all.spawn`); the original Bar `level.spawn` the same way (`coop_l05_bar\level.spawn`, `gamedata.db0`).
- Applied (with `--ref`) to `darkvalley_restore\gamedata\spawns\all.spawn` AFTER `no_tech_parts` had stripped the parts (the steps compose: both
  select by content, the order does not matter; both `--check` runs are clean on the result) and to the skipped `soc_levels\gamedata\spawns\all.spawn`.
  When `make_all_spawn.py` regenerates `all.spawn`, run `strip_spawn.py` and then this tool again (no `--ref` needed: a regenerated file is the original
  plus the two additions, it only has to lose FOSTER's zone).
- `gamedata\levels\coop_l05_bar\level.spawn`: the Bar's original `level.spawn` (from the add-on) without FOSTER's chunk (570 of 571), chunk ids renumbered.
- Other `gamedata` files of this patch: none, so `check_conflicts.py` sees no new duplicate. No script respawns anomalies.

## Test
Offline (run, 2026-10-21): `strip_bar_anomalies.py --check --ref <original> <all.spawn>` is clean for both files, `--report` marks one zone REMOVE and keeps
the other 59, a second run changes nothing, graph and artefact chunks are identical to the original, `no_tech_parts	ools\strip_spawn.py --check` clean.
In game (written, not run: offline task): `tests\bar_no_anomaly_hooks.lua` (listen mode, start on Cordon, `-Cfg no_respawn=1`): travels to the Bar through the
guide flag and the party vote and asserts that FOSTER's zone `level_prefix_zone_mine_gravitational_strong` is absent and the nine named zones above
exist. Command in the header of the file.

## RU (кратко)
Фостер: на Баре прямо перед переходом стоит аномалия, слишком близко к точке появления. Это штатная гравитационная аномалия ТЧ
(`level_prefix_zone_mine_gravitational_strong`, 12 м от точки прихода со Свалки). В версии 1.4.1 было убрано 10 аномалий; Фостер ответил "верните все, кроме одной",
поэтому в 1.4.2 убрана только его аномалия (354.7, 9.3, -178.0), остальные 9 возвращены как в оригинальном ТЧ (`all.spawn` и `level.spawn`).
Костры и `camp_zone` не трогаются. Инструмент: `tools/strip_bar_anomalies.py` (`--ref` возвращает недостающие), тест: `tests/bar_no_anomaly_hooks.lua`.
