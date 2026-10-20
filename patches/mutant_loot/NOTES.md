# mutant_loot - notes

## What it does
Search a dead mutant like in Shadow of Chernobyl and take its part (dog tail, flesh eye, ...). One SoC roll per corpse when the mutant dies (chance 0.2 for the eight SoC parts, the add-on's own chances for tushkano, controller, chimera, gigant; `configs/misc/mutant_loot.ltx`). The result is a shared story flag per corpse and part (`MLOOT_<corpse id>_<PART>`), so every player sees the same content. A dead mutant that can carry a part shows the tip "Search"; Use opens a small window (the xrMPE engine cannot open the inventory of a monster). Take sends `mloot_take_<id>` to the server, which removes the flag first and then creates the part in the taker's inventory: one part per corpse, no duplicate, also when two players press Take in the same tick.

## Files
* `scripts/mutant_loot.script`, `scripts/ui_mutant_loot.script`, `configs/ui/mutant_loot_wnd.xml`, `configs/misc/mutant_loot.ltx`, texts (eng, rus).
* `bind_monster.script` is NOT shipped here. The hooks live in the merged copy in `patches/darkvalley_restore` (poltergeist corpse + `coop_balance.on_npc_hit` + mutant_loot hooks). Ship both patches together; `tools/gen_bind_monster.py` shows the four edits.
* `tests/loot_test.lua` is a test hook (never shipped).

## Tests (dedicated server + 2 real clients on Cordon, `tools/stalker_xrmpe/run_coop.ps1`)
Merged gamedata = cnpp_shake + task_guard + darkvalley_restore (without all.spawn) + soc_economy + mutant_loot. Chance forced to 1.0 by the test hook:
* a dog and a flesh are spawned next to player 1 and killed by a hit whose draftsman is player 1 (death credited to player 1);
* both clients see the right part on each corpse and the Search tip and use callback armed on it;
* player 1 takes the dog part (the function the Take button calls): it is in player 1's inventory on the client; player 2 then takes the same corpse and gets nothing (server take log: player 1 ok 1, player 2 empty 0); both clients agree the corpse is empty, the tip stays, the empty window opens;
* player 1 and 2 request the flesh part in the same tick: exactly one part exists;
* run with default chances (0.2): 10 mutants killed, the server used 0.2 for each, both clients show exactly the corpses the server rolled (4 of 10 won), no crash.
The window cannot be clicked by a bot; the test calls `ui_mutant_loot.open` and `mutant_loot.request_take`, the same functions the window and its Take button use.

## Кратко по-русски
Обыск трупа мутанта как в оригинальной SoC: один бросок на труп (0,2 для частей SoC), часть лежит в трупе, общая для всех игроков; забирает первый нажавший, второй ничего не получает. `bind_monster.script` объединён в `darkvalley_restore`; ставить оба патча вместе.
