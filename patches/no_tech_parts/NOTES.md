# Technician parts removed (transistors, rosin, capacitors, copper wire, textolite)

## Request
Maintainer FOSTER, with screenshots (a "Box of transistors" in the inventory, two coils of copper wire on lockers in a house):
cut all these transistors, rosin, capacitors and copper wire from the game world and from the add-on, they are for the Bar technician, and
cut the Bar dialogs about bringing them to him. They are not in the original SoC (they are Call of Pripyat quest items of the Jupiter job `jup_b200`).

## The item family (sections kept, so old saves load)
All five come from the mod's `configs\misc\quest_items_addon.ltx` (`can_trade = false`, no cost, never sold):

| Section | Name in game (EN / RU) |
|---|---|
| `jup_b200_tech_materials_transistor` | Box of transistors / Коробка транзисторов |
| `jup_b200_tech_materials_acetone` | Can of rosin / Банка канифоли (the section name says acetone, the texts say rosin) |
| `jup_b200_tech_materials_capacitor` | Pack of capacitors / Упаковка конденсаторов (inherits `guitar_a` in the mod, a copy-paste slip; unchanged) |
| `jup_b200_tech_materials_wire` | Coil of copper wire / Моток медной проволоки |
| `jup_b200_tech_materials_textolite` | Textolite base / Текстолитовая основа (the 5th item of the same technician dialog) |

The sections and their strings stay defined. An item already in a player's inventory or on the ground of an old save stays too.

## Where they came from and what was done
Searched in: the mod's db0/db1 sources, the xrMPE/CoP base configs, every patch, the raw bytes of `all.spawn`.

| Source | Found | Done |
|---|---|---|
| World spawns (`spawns\all.spawn`, no `level.spawn` is used) | 63 objects: Cordon 26, Garbage 16, Agroprom 21 (wire 30, capacitor 9, transistor 8, rosin 8, textolite 8), no other level, no box holds them, none has a parent | removed by `tools\strip_spawn.py` in `darkvalley_restore\gamedata\spawns\all.spawn` (the file all patches build on) and in `soc_levels\gamedata\spawns\all.spawn` (not shipped yet). The other objects keep their order, ids are made contiguous again and the `spawn_id` field of every packet is rewritten (it equals the chunk id in this file); chunks 2 to 4 (artefact points, patrol paths, game graph) are untouched |
| Box loot (`stash_loot`), corpse and death loot (`corpse_artifacts`, `death_items_*`), mutant loot, trader assortments and supplies, quest rewards, repeatable / fetch quests (`gen_fetch`), treasure tables | none of them names a part or draws from a list that contains one | nothing to remove |
| Dialogs | Bar technician Plyushkin: "What kind of junk do you need?" and "I have something..." (1000 RU per 3 pieces, 5 items). The same two dialogs were also copied into the character files of the Army Warehouses technician Shurup and of Max (`character_desc_coop_l07_military.xml`) | both dialogs deleted from `quest_dialogs\...\dialogs_coop_l05_bar.xml`, their `actor_dialog` lines deleted in `repeatable_quests\...\character_desc_coop_l05_bar.xml` and `freedom_duty\...\character_desc_coop_l07_military.xml`; `quest_dialogs\gen_quest_dialogs.py` drops them when it regenerates the Bar file |
| Lua helpers | `if_actor_has_materials_*_3x` and `transfer_materials_*_3x` (5 + 5) in `dialogs_item.script` | removed from `artifact_quests\...\dialogs_item.script` |
| Greeting | the technicians' start line was "Hello, brought anything?" (asks for the parts) | now "Hello. Something broken?" / "Здоров. Что-то сломалось?"; this patch ships `configs\text\eng|rus\st_dialogs_coop_l05_bar.xml` (the mod's file without the 11 dead strings, greeting replaced) |
| Upgrades | the technician's upgrades never needed the parts: `stalkers_upgrade_info.ltx` has no parts condition, `item_upgrades.ltx` and `inventory_upgrades.script` do not mention them. The only link was a price discount for the parts handed in (`jup_b200_tech_materials_brought_counter_*`), and that line is commented out in the mod, in `cordon_technician` and in `weapon_upgrades` (factor 1.0) | nothing to change: upgrades and repair work as before without any part |

Left on purpose (listed by `tests\offline_check.py`):
* `configs\misc\trade\*.ltx` of `soc_economy` (4 files) and `yantar_restore` (1): five bare "NO TRADE" lines in the sell list of the traders. They only name the
  sections (which cannot be traded anyway), offer nothing and give nothing; left so that the other patches keep their copies.
* `configs\text\*\st_quest_items.xml` of `freedom_duty`: the item names and descriptions of the kept sections.
* `cordon_technician\NOTES.md` and `soc_levels\swap_report.txt`: old text that mentions the items.
* The mod's Jupiter leftovers (`dialogs_jupiter.xml` etc.) mention them but no character of a SoC level uses them.

## Regenerating files
* `all.spawn`: if `darkvalley_restore\tools\make_all_spawn.py` (and then `cordon_bridge\tools\make_paths.py`) rebuilds the file, run
  `python patches\no_tech_parts\tools\strip_spawn.py <all.spawn>` on the result LAST (`--check` only counts).
* Dialog and text files: `python patches\no_tech_parts\tools\strip_dialogs.py <mod gamedata.db0 folder>` (idempotent) redoes the dialog xml, the two
  character files, the Lua helpers and the two text files.

## Checks (offline, 2026-10-21)
* `python patches\no_tech_parts\tests\offline_check.py <db0> <db1>`: both `all.spawn` files have 0 parts, ids contiguous, `spawn_id` == chunk id, header count right;
  no patch file refers to the sections or the cut dialogs except the leftovers above; every `dialogs_item.*` function used by a dialog exists; every
  dialog id of the Bar and Military characters exists; the greeting strings exist in both languages. Result OK.
* Round trip of the spawn reader/writer is byte identical; after the strip chunks 2 to 4 are byte identical and every other packet equals the old one
  except its `spawn_id`.
* `check_conflicts.py`: only the 7 known overlaps, this patch adds none. `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing`:
  `verify_db` 0 problems, `BUDGET OK` (headroom about 24 MB). The merged stage has no part in `all.spawn` and no reference outside the leftovers.

## Test plan (NOT RUN, no game was started)
`tests\no_parts_hooks.lua`, listen mode, one game process, start on Cordon and travel (the Bar alife only comes online after a travel):
```
run_coop.ps1 -Map coop_l01_escape -Owner noparts -Mode listen -Clients 1 -Cfg no_respawn=1 -ExtraDir <stage>\gamedata -Hooks <path>\no_parts_hooks.lua -SoakSeconds 240 -CompareTimeout 10 -ResultDir <dir>
python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix NP --require 12
```
Expected: on Cordon and again on the Bar, a scan of all 65535 alife slots finds 0 objects of the five sections (and none with `tech_materials` in the name); the
technician greeting string no longer says "brought anything"; the cut dialog strings translate to themselves (are gone); the Lua helpers are nil; Plyushkin is
online on the Bar, `inventory_upgrades.can_upgrade_item("wpn_pm", <his profile>)` is true (upgrades work without parts), his talk window opens (`is_talking`).
The buttons of the talk window cannot be driven by the harness; the dialog list itself is proven only by the offline check (every id the characters list exists, none
of the cut ones is listed).

## Кратко по-русски
Убраны детали для техника, которых нет в SoC: коробка транзисторов, банка канифоли, упаковка конденсаторов, моток медной проволоки (и пятая, текстолитовая основа).
Из `all.spawn` вынуты все 63 предмета (Кордон, Свалка, Агропром); ящиков, трупов, торговцев и заданий с ними не было. У Плюшкина в Баре (и у техника Шурупа и Макса,
у которых скопированы те же диалоги) удалены диалоги "Что тебе нужно из хлама?" и "Есть кое-что...", функции Lua и фраза приветствия "принёс чего?".
Улучшения этих деталей никогда не требовали (только скидка за сданные детали, строка и так закомментирована), поэтому работают как раньше.
Секции предметов оставлены, чтобы старые сохранения не падали. В игре не проверено, план теста в `tests\no_parts_hooks.lua`.
