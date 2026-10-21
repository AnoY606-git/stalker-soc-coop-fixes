# mutant_loot - notes

## What it does
Search a dead mutant like in Shadow of Chernobyl and take its part (dog tail, flesh eye, ...). One SoC roll per corpse when the mutant dies (chance 0.2 for the eight SoC parts, the add-on's own chances for tushkano, controller, chimera, gigant; `configs/misc/mutant_loot.ltx`, overridable by the host through `coop_host_cfg` keys of section `mutant_loot`). The result is a shared story flag per corpse and part (`MLOOT_<corpse id>_<PART>`), so every player sees the same content. A dead mutant that can carry a part shows the tip "Search". Pressing Use on it gives the part straight to the player who pressed Use, takes the flag away first (one part per corpse, no duplicate, also when two players press in the same tick) and shows "Found: <part>" or "Nothing useful on the body" to that player only.

## Why it did not work in real play (cause, found 2026-10-21)
The first version armed the use callback on every machine but only acted when `who` was the machine's own local actor, and then opened a small window (Take button) on that machine. In xrMPE the use callback of a monster is run by the script binder that owns the object, which is the SERVER binder (listen host or dedicated), with `who` = the actor that pressed Use, also for remote players. Evidence from the code: the other use callbacks of the mod (sr_button restrictors, ph_button / ph_code scheme logic, boxes) are armed in binders that only exist on the server, and the MSO add-on (below), which FOSTER reports as working, arms it in the server binder only (its client binder has no use method at all). So:
* dedicated server: the callback ran with who = a client actor, `who ~= LocalActor()` was true, it returned at once: nothing happened for anybody;
* listen host: only the host's own presses reached the window code, every remote player's press was dropped;
* the old test only called `request_take` and `ui_mutant_loot.open` directly and checked that the callback was "armed", never that the engine fires it on a client, so it passed.
The window (`ui_mutant_loot`) was also never seen on a real screen. It is gone: Use takes the part directly, like the MSO add-on, and there is no UI that can fail.

## What was adopted from the MSO add-on
`xrmpe_mso_adaptation` ("MSO Call of Pripyat Co-op Beta", adapted by B4rs1k, made by Salaam; its mutant looting code in `bind_monster.script` / `nz_loot.script` / `game_cl.script` is marked fluffy22 with credits to the ARS and TGZ teams). Taken from it: the use callback lives in the server binder of the dead mutant, is re-asserted on every update (we do it once a second) together with `set_tip_text("st_mutant_loot_tip")` on every machine, `who` is the actor that gets the loot, the server creates the item inside that actor, and the player gets a "found / nothing" tip. Not taken: its per-corpse random rolls at Use time, its `looted` flag in `se_monster` (needs `STATE_Write` changes), its loot table by clsid and its own GM message type. We keep SoC parts and chances, the roll at death, the flag per corpse (saved with the game, synced to everybody) and `bind_monster.script` as it is in `darkvalley_restore` (no change needed there: `tick_dead` is called by the same hooks).

## How it works now (mutant_loot.script)
* `on_death` (server, from the binder): one roll, flag `MLOOT_<id>_<PART>` if won, game function `mloot_take_<id>` registered.
* `tick_dead` (server binder update and the client binder, every machine): every second `set_callback(callback.use_object, mutant_loot.use_cb, binder)` and the Search tip; polls the feedback flags.
* `use_cb(binder, corpse, who)` = what the engine calls on Use. On the server: `use_server(who id, corpse id)` (ignores a repeat from the same player and corpse within 1.5 s, flag off first, `alife():create(part, ..., parent = player)`). On a client machine whose engine fires the callback itself (kept as a fallback): asks the server through `game_cl.executeFunctionOnServer("mloot_take_<id>")` only when the corpse still shows a part.
* Feedback: the server gives a short-lived flag `MLOOTR_<player>_<corpse>_<random>_<CODE>` (`OK_<PART>` or `EMPTY`), the corpse binder on that player's machine (within 20 m) shows the tip through `news_manager.send_tip` (icon mutant_hunter). Flags that exist when the corpse binder first polls are ignored, and the server removes old ones on the first use of a session. No game_cl change, no new message type.

## Files
* `scripts/mutant_loot.script`, `configs/misc/mutant_loot.ltx`, texts `configs/text/{eng,rus}/st_mutant_loot.xml` (tip, found, nothing useful).
* `bind_monster.script` is NOT shipped here. The hooks live in the merged copy in `patches/darkvalley_restore` (client binder, dead-mutant tick, death roll, alive-spawn reset). Ship both patches together; `tools/gen_bind_monster.py` shows the four edits.
* `tests/mutant_loot_mock_test.py`: offline check of the real script in a Lua VM with a mock engine (`pip install lupa`, `python tests/mutant_loot_mock_test.py`, 31 checks: roll, arming, use by the server callback, one part per corpse, repeat and double fire, second player, race, far player, NPC user, feedback only on the right machine, client fallback).
* `tests/loot_test.lua`: game hook (never shipped), see the test plan.

## Test plan (single listen host, the coordinator runs it)
Merged gamedata = mutant_loot + darkvalley_restore + soc_economy (+ the rest of the release set). One listen host with one client slot:
```
run_coop.ps1 -Map coop_l01_escape -Owner <name> -Mode listen -Clients 1 -ExtraDir <stage>\gamedata -Hooks <repo>\patches\mutant_loot\tests\loot_test.lua -SoakSeconds 120 -CompareTimeout 10 -ResultDir <dir>
python tools\stalker_xrmpe\qa_verdict.py <dir>
```
The hook spawns a dog, a boar and a flesh next to the player (god mode on), kills them with the player as attacker (chance forced to 1.0), then for each corpse calls `mutant_loot.use_cb(nil, corpse, actor)`, the function the engine's use callback runs (a bot cannot press the Use key), and asserts: the roll and the flag, the callback armed by the server binder, the part in the inventory (online walk) and exactly one on the server, the corpse flag gone, a second use gives nothing, tips "Found" and "Nothing useful". `-Cfg mode=default` repeats it with 6 corpses at the real chance 0.2. After the run read `mutant_loot.log` in the logs folder: a line `use corpse=<id> by=<actor> server=true` per press.
To check the engine side for real (what no bot can do), a human or a later bot needs to press Use on a corpse: the log line `use corpse=` appears in `mutant_loot.log` on the machine where the binder runs; with a dedicated server and a remote client that line appears in the SERVER's log with `by=` the client's actor id, and nothing appears in the client's log. If the engine fires the callback on the client instead, `use_client` asks the server and the log shows `server=false` plus a `take actor=` line on the server.

## Кратко по-русски
Обыск трупа мутанта как в оригинальной SoC: один бросок на труп при смерти (0,2 для частей SoC), часть лежит в трупе, общая для всех игроков. Use на трупе сразу отдаёт часть тому, кто нажал (один экземпляр на труп, второй игрок ничего не получает), подсказка "Найдено: ..." или "На теле нет ничего полезного" только ему.

Причина, почему не работало: колбэк Use монстра в xrMPE вызывается серверным биндером (хост или выделенный сервер), в `who` приходит актёр нажавшего, в том числе удалённого игрока. Старый код действовал только если `who` равен локальному актёру своей машины и открывал окно: на выделенном сервере и для чужих игроков всё молча отбрасывалось. Старый тест вызывал функции напрямую и никогда не проверял, что движок вообще вызывает колбэк.

Исправление по образцу дополнения MSO Call of Pripyat Co-op (адаптация B4rs1k, автор Salaam, код лута помечен fluffy22, благодарность командам ARS и TGZ): колбэк и подсказка "Обыскать" ставятся заново каждую секунду, сервер выдаёт часть актёру из `who`, игрок получает сообщение. Окна больше нет. `bind_monster.script` по-прежнему в `darkvalley_restore`, ставить оба патча вместе.
