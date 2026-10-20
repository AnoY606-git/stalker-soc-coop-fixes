# No grenade ringing - notes

## Request
Players asked to cut the ear-ringing (tinnitus) sound after grenade explosions and flashes.

## Change
`gamedata/configs/creatures/actor.ltx` (copy of the mod's file, two lines changed in `[actor_hit_snds]`):
`explosion` and `flash` now play `weapons\silence` (the silent sound the mod already uses for burn/radiation hits) instead of
`affects\tinnitus_explosion` / `affects\tinnitus_flash`. Damage, camera shake and everything else are unchanged.
The scripted tinnitus of teleports (`sr_teleport`) is not touched.

## Note
This file replaces the whole actor.ltx: if a future mod version changes actor.ltx, redo the two-line edit on the new file.

## Кратко (RU)
Убран звон в ушах от взрывов гранат и вспышек: в `[actor_hit_snds]` звуки `explosion` и `flash` заменены на `weapons\silence`. Урон и тряска камеры без изменений.
