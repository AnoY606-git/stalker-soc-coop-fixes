# Inventory carry (player bodies after a save load)

## Problem (player reports, v1.3)
- After loading a save, the weapon in a slot is replaced by a backpack weapon and the slotted one is gone (until the next load).
- After loading a save only the host keeps the kit; clients come back with no outfit, no weapons, no money, only the start kit.
- Related open item: the host's armor swapping after some level changes.

## Root cause
Found by dumping every body (id, name, slots, inventory, parent) on the server and on the client around `game_sv.saveGame`
and `game_sv.loadLastSave`:
- A save keeps each player's body (the actor entity) with all its items. Items keep their own slots across the load
  (slot items of the saved body were identical before and after).
- After the load the engine does NOT give that body back to the reconnecting player. It spawns a NEW body with only the start kit
  (knife, torch, binoculars, PDA, bolts) and leaves the saved body in the world with nobody controlling it. On a dedicated server
  the saved body is renamed `actor_the_main_character`; in a listen game both bodies carry the player's name. The host sometimes
  keeps his saved body (the engine recognises his own connection), clients never do.
- Every further load adds another body: the next autosave contains old and new bodies, so "the old weapon reappears after the
  next load" is the same saved body showing up again. The "wrong weapon in the slot" is the player seeing the new or the old
  body's slots depending on which one the client currently controls.
- Not the cause: item order, `give_start_item` (only fires from the Cordon restrictor), `no_mp_items`.

## Fix (`gamedata\scripts\coop_scn_inventory_carry.script`, server only)
- Every living player body is remembered in a story flag `PBODY_<NAME>_<body id>`. Story flags are written into the save and
  restored by the load (same mechanism as the `PSC_` flags of `player_scaling`).
- When a player has two bodies (a flagged body that is still in the world plus a newer body that carries his name), the items of
  the old body are MOVED (`transfer_item`, same item ids, nothing re-created, conditions / magazine ammo / upgrades kept) to the
  new body: slotted items first in slot order so they take the empty slots again, then the rest in batches. Money is moved too.
  Start-kit sections the new body already has are not moved a second time (no duplicates). When every item is verified on the new
  body, the empty old body is released and the flag moves to the new body. If an item cannot be moved, the old body is kept.
- Replaces the earlier unproven `inventory_carry` idea (re-creating missing items from a file), so this patch now covers its goal.

## Test (dedicated server + 1 and 2 clients, listen host; harness `slot_hooks.lua`)
Each player gets 2 rifles, 2 pistols, 2 outfits (the higher-id ones are slotted, the others in the backpack, set up with
transfer_item through a holder NPC) and money; `game_sv.saveGame`, then `game_sv.loadLastSave` twice. Pass = the same weapons /
outfit in the same slots, same money, same item counts, exactly one living body per player (checked on server and client).
Stock (before): the player's new body has no weapon or outfit in any slot and 0 money, the saved body stays as a second living body.

## Кратко (RU)
После загрузки сохранения движок не возвращает игроку его сохранённое тело, а создаёт новое только со стартовым набором; старое
тело остаётся в мире без владельца (у хоста иногда сохраняется, у клиентов никогда). Отсюда пустой инвентарь у клиентов и
"чужое оружие в слоте". Фикс: сервер запоминает тело каждого игрока флагом PBODY_ИМЯ_ID (флаги пишутся в сохранение) и после
загрузки переносит предметы старого тела в новое (transfer_item, те же предметы, сначала слотовые, чтобы встали в те же слоты),
переносит деньги и удаляет пустое старое тело. Дубликатов нет: предметы перемещаются, а не создаются.
