# freeplay: keep playing on the Cordon after the true ending

Request (FOSTER, agreed with Akasi, approved by the owner): after the true ending the game should not end. The players are brought back to the Cordon (rookie village)
with their inventory, the world keeps running (repeatable jobs, traders, every level incl. the new ways back), the story flags stay set so nothing replays. Host setting
`[freeplay] enabled = true` (default), `false` = the old behaviour.

## What the mod did (before)
`cutscenes_pkg_endings\gamedata\scripts\coop_scn_endings.script`: the true ending is the scene `end_peace` on `coop_l11_stancia_2` (flag `AES_2_THE_END_SPACE_RESTRICTOR_INFO`,
movie `final_peace`, 106 s). Its `on_end` requests the scene `credits` (the original `credits_seq`, 295 s, majority may skip), whose last step is `main_menu`
(ack, then `disconnect` for everybody) and whose `on_client_end` also calls `go_to_menu`. The wish-granter endings (`end_wish`) and "join the C-Consciousness"
(`end_join` in `cutscenes_pkg_monolith`) request the same credits. Result: everybody lands in the main menu, the game is over.

## What it does now
```
end_peace (movie) -> credits (variant "freeplay": no main_menu step, no disconnect) -> scene "freeplay" -> party teleported into a level changer -> Cordon rookie village
```
1. `coop_scn_endings.script` (3 small edits): `end_peace.on_end` asks `coop_scn_freeplay.credits_variant()` (server) and requests `credits` with that variant; the credits
   steps of the variant `freeplay` end with `ui_on` instead of `main_menu`; `credits.on_client_end` does nothing for the variant. Without the variant everything is as before.
   The wish endings and the join ending never use the variant: they still end in the main menu (the owner asked for the TRUE ending only).
2. `gamedata\scripts\coop_scn_freeplay.script` (loaded by the Scene Director like every `coop_scn_*.script`):
   - `credits_variant()`: server only; `[freeplay] enabled` (host file, default true) -> gives the shared flag `COOP_FREEPLAY_PENDING` and returns `"freeplay"`; off -> `nil`.
   - scene `freeplay` (level CNPP-2, once, skip none, 5 s): trigger = PENDING and the credits scene is over (`SCN_CREDITS_PLAYED`); `on_go` gives `COOP_FREEPLAY_OPEN`, the clients show a
     news line (`scn_freeplay_caption/msg`, EN + RU); `on_end` calls `transfer()`.
   - `transfer()`: gives `COOP_FREEPLAY_DONE`, then `teleport_actor_sv` of every ALIVE player into the exit (the server object `aes_2_esc_freeplay_level_changer`, its
     position; the constants are the fallback) - the same call the Cordon guide uses to push the party into a level changer. Idempotent.
   - every machine, 1 s tick (the pattern of `garbage_duty`): the exit is switched off with `enable_level_changer(false)` until `COOP_FREEPLAY_OPEN` exists, so nobody can walk
     into it before the ending. The server takes OPEN away again once the party is on another level (the exit is closed for good).
   - watchdog: 25 s after the teleport, if the level is still CNPP-2, the shared flag `COOP_FREEPLAY_FAILED` sends everybody to the main menu (the old behaviour; clients after 2 s,
     the host after 5 s), so a broken exit never leaves the party stuck at the end of the game.
3. The exit: level changer `aes_2_esc_freeplay_level_changer`, CNPP-2 (981.7 0.0 337.7, 6 x 8 x 6 m, the far south east corner of the level, 1000 m from where the Control
   Monolith exit lands, on the AI mesh, 64 nodes inside) -> Cordon, game vertex 53 (-199.0 -19.9 -140.6) = the rookie village, 8 m from the campfire. Written by
   `patches\level_back\tools\add_level_changers.py` (the one step of the shared `all.spawn`).
4. `host_settings\...\coop_host_cfg.script`: new group `[freeplay]`, key `enabled` (bool, default true) with the EN and RU description. The file `coop_settings.ltx` gets it
   like every other key (an old file keeps working, the key then uses the default true). Server only: the clients learn the decision through the credits variant.

## What stays as it is (the story flags)
Nothing is reset: no flag is removed (the scene flags `SCN_*_PLAYED`, quest infos, task states, the repeatable-job state and everything in the save stay), only
`COOP_FREEPLAY_PENDING` / `_OPEN` / `_DONE` are added (`_OPEN` is removed again after the arrival). Because the director's scenes are `once` and the late-join baseline never replays a
GO flag, the opening, the Radar and Pripyat scenes and the endings do not play again. The inventory travels with the level change as for every other level change (the known
open item "armor of the host swaps on some transitions" of `stalker.md` is the engine's level change, not this patch). Money and quest items are not touched.
Dead players are not teleported; they come back through the normal respawn on the new level.

## Known limits (honest)
- Nothing here was run in the game (offline task): the exit is a normal level changer cloned from an existing one, and the teleport is the call the guide uses, but whether the
  engine takes the whole party through a changer that was entered by a scripted teleport on CNPP-2 is proven only for the guide changers on the Cordon. The watchdog covers it.
- Whether the engine shows the "Move the whole squad to the next location?" prompt for this exit is not known; with the prompt each player answers yes.
- The switch-off needs `level.object(exit)` on the machine (the same call `garbage_duty` uses for the Garbage gate). If the changer is not online on a machine, the exit keeps its spawn state (open) there; it stands 1000 m from every route in the far corner, so this only matters for a player who walks there on purpose.
- After the party is back on the Cordon the CNPP-2 exit is closed again (OPEN removed), so walking back to CNPP-2 with the guide and into the corner does nothing.
- The wish-granter endings and the "join" ending still end the game (menu).

## Tests
- Offline, a few seconds: `python patches\freeplay\tests\freeplay_mock_test.py` (needs `pip install lupa`): runs the REAL `coop_scn_freeplay`, the REAL edited `coop_scn_endings` and the
  REAL `coop_host_cfg` in a Lua 5.1 VM with an engine mock. 50 checks: the host switch (default on, off, no `coop_host_cfg`, client), the credits variant and PENDING flag, the credits steps with and
  without the variant (no `main_menu`, no disconnect for freeplay; old path unchanged; wish ending unchanged), the scene trigger (PENDING + played credits only), `on_go` OPEN, the news
  line, `transfer` (2 of 3 players alive -> 2 teleports into the exit position, DONE, idempotent, every story flag still there, only DONE added), the fallback position, the exit
  closed on every machine until OPEN, closed again after the arrival, the watchdog (FAILED -> disconnect; no FAILED when the level changed), both text files. Also
  `patches\host_settings\tests\host_cfg_mock_test.py` (the new key is in the created file with EN and RU text, `false` in the file is read).
- Game hook (not run here): `tests\freeplay_hooks.lua` (header: modes `quick` / `full`, switched-off run). Stage 0 gives every player 3 medkits, 2 bread and 12345 money, marks a story
  flag and travels to CNPP-2 with the guide vote; stage 1 sets the final-scene flags (`AES_2_THE_END_SPACE_RESTRICTOR_INFO`, `SCN_END_PEACE_PLAYED`, quick mode calls `end_peace.on_end`
  the way the director does), waits for the credits, votes to skip them for every player and waits for the level change; stage 2 on the Cordon asserts: all players there and alive, medkits,
  bread and money equal to the record, everybody within 120 m of the village arrival point, the marker flag and `SCN_END_PEACE_PLAYED`, `SCN_CREDITS_PLAYED`, `COOP_FREEPLAY_DONE`,
  `AES_2_THE_END_SPACE_RESTRICTOR_INFO` still set, `COOP_FREEPLAY_OPEN` gone, no played scene lost and none added except credits / freeplay / end_peace, NPCs alive around the village.

```
cd <repo>
python build.py <out>\zzz.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing
powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner fpquick -Mode listen -Clients 1 `
  -DbFile <out>\zzz.db -Hooks <repo>\patches\freeplay\tests\freeplay_hooks.lua -Cfg no_respawn=1 -SoakSeconds 600 -CompareTimeout 10 -ResultDir <dir>
python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix FP --require 25
```
The live saves cannot be used (made with the v1.3 `all.spawn` without the new exit): the run starts on a fresh Cordon and travels to CNPP-2 with the guide vote (about 70 s). Total about 5 minutes in `quick` mode.
For the long run with the real movie make a copy of the hook with `local MODE = "full"`; for the switched-off run a copy with `local OFF = true` (the old end: the credits end with the
disconnect, the run stops, the hook asserts only that no freeplay flag exists).

## Кратко по-русски
После истинной концовки (`end_peace` на ЧАЭС-2) игра больше не заканчивается: титры идут как раньше, но без выхода в главное меню, затем вся группа (живые игроки) телепортируется в
выход `aes_2_esc_freeplay_level_changer` и попадает на Кордон в деревню новичков со всем инвентарём и деньгами. Сюжетные флаги не сбрасываются (сцены `once` не повторяются), мир, торговцы,
повторяемые задания и все локации (включая новые обратные переходы с Радара и из Припяти) работают. Настройка хоста в `coop_settings.ltx`: `[freeplay] enabled = true` (по умолчанию),
`false` = как раньше (титры и главное меню). Если смена локации не сработала за 25 с, все выходят в главное меню (как раньше). Концовки у исполнителя желаний и "присоединиться к
Сознанию" по-прежнему завершают игру. Тесты: `tests\freeplay_mock_test.py` (50 проверок без игры), `tests\freeplay_hooks.lua` (игровой).
