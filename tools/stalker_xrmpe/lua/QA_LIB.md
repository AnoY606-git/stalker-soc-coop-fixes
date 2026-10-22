# qa_lib: test-bot library for Shadow of COOP (xrMPE 0.9)

`lua/qa_lib.lua` collects the code that the test hooks in `stalker-soc-coop-fixes\patches\*\tests\*.lua` kept re-writing: travel through
the party vote, flags, items, NPC spawns, hits, saves, talk windows, screenshots. Test-only, never shipped.

## Load it
The harness appends your hook file(s) to three shipped scripts of a test addon copy. Either:
1. first line of your hooks file: `--@qa_lib` (opt-in marker; `qa_build.py` then appends `qa_lib.lua` right before your file, once), or
2. `run_coop.ps1 -Hooks "C:\...\lua\qa_lib.lua,C:\...\my_hooks.lua"`.

Then `local L = qa_lib` (also `qa.lib`). Offline check without the game (a few seconds): `python tools\stalker_xrmpe\qa_lib_mock_test.py`.
Example users: `lua\qa_lib_smoke.lua` (every function), `lua\qa_lib_regress.lua` (the 1.2 fixes), `lua\newagent_test_hooks.lua` (hostile NPC near the
village fire, hits, save/load), `stalker-soc-coop-fixes\tools\release_boot_travel.lua` (Bar boot check of `release.py`).
Version 1.2 (2026-10-21).

## Rules that matter
- **Hooks files run 3 times per VM.** `run_coop` appends your hooks file to three shipped scripts that load at different times. With qa_lib loaded,
  `qa.once("name", fn)` (also `L.once`) ignores a second registration of the same name in the same VM, so the body runs ONCE per VM (a new VM,
  after a level change or a player death, runs it again: use `L.state_get/set` for "already done"). Code at the top level of your file outside
  `qa.once` still runs once per load: keep it to function definitions.
- **Call `L.god(true)` BEFORE you spawn a hostile NPC** (or pass `god=true` to `spawn_npc`). A bandit 4 to 6 m from the player kills him within
  seconds; the VM restarts and your test starts over. `spawn_npc(..., relation="enemy")` logs a `WARN` line when god mode is off.
  `hits_to_kill` only sets god mode for its own duration.
- **`RESULT: FAIL` from run_coop is often noise.** After a respawn or a level change the comparer reports `A sees player id N that no client
  reports as itself` (a presence mismatch, not a bug). Get the real outcome with `python tools\stalker_xrmpe\qa_verdict.py <ResultDir> [--prefix NA]`:
  it counts the asserts of every client_* folder, lists FAIL lines and real compare problems, and prints `VERDICT: PASS|FAIL`.
- **A queued run leaves an empty result folder** (run_coop writes `run.log` only after it got a slot lease). `qa_verdict.py` says QUEUED/EMPTY
  then; look at the queue with `python tools\stalker_xrmpe\stalker_slot.py status`. `release.py` writes `STATUS.txt` and a live `release_stdout.log`
  into every boot folder.
- **Disk:** the lanes need 10 GB free beyond them. Do not launch below 10 GB free (`release.py` waits).
- **A level change restarts the Lua VM** (the harness logs `previous nil`). Keep progress in `L.state_set/get` (file `$logs$\qa_lib_state.txt`);
  `L.travel_arrived()` tells the new VM that a travel finished.
- **NO COROUTINES.** In this engine `coroutine.create/resume` hard-crashes LuaJIT (`lua_getinfo` in the stack trace; proven with
  `lua\qa_lib_diag.lua`, run `botlib_diag1`, 2026-10-20). Anything that needs game time to pass is an **ACTION**
  (a table with a `tick` function). Library functions that wait (travel, hits_to_kill, teleport, save, open_talk, screenshot,
  kill_player, wait, wait_for) RETURN an action. Run them in a task:
  ```lua
  L.task("my test", {
      function(c) return L.wait(5) end,
      function(c) return L.teleport(nil, {-243, -24.2, -135}) end,        -- result goes to the next step
      function(c, ok, how) qa.assert("moved", ok, how) return L.hits_to_kill{ power = 0.5518 } end,
      function(c, res, err) qa.assert("killed", res and res.killed, res and res.hits) end,
  })
  ```
  A step may return an action (its results are the arguments of the next step), `L.again(sec)` (loop), `L.jump("label")`, `L.done(...)`,
  or any value (passed on, next step runs at once). `L.protect(seq, name)` turns an error inside a part into one FAIL line.
- **The engine's Lua health setter is RELATIVE**: `obj.health = x` adds x. Use `L.set_health(obj, v)`.
- Server-side calls (spawn, give_item, hit, kill, save) run where `alife()` exists: the listen host or the dedicated server role S.
  Client-side calls (open_talk, screenshot) need a real client or the listen host.
- Every call writes `LIB ...` lines to `qa_events.log`. Failures return `nil/false, reason`.

## Functions
| Area | Function | Notes |
|---|---|---|
| state | `state() / state_get(k, default) / state_set(k, v) / state_clear()` | survives level changes |
| tasks | `task(name, steps)`, `seq`, `protect`, `wait(sec)`, `wait_for(cond, timeout)`, `now(...)`, `done / jump / again` | actions, see above |
| players | `players([dead])`, `player(spec)`, `local_player()`, `pos(spec)` | spec: nil, id, name ("qaa"), object |
| health | `set_health(o, v)`, `heal(o)`, `god(on)` | god tops every alive player up each tick |
| flags | `flag_give/flag_clear/flag_has(name)` | story flags: shared, synced, saved |
| info | `info_give/info_clear/info_has(name [, player])` | engine info portions, per player |
| money | `money(p)`, `give_money(p, n)` (delta), `set_money(p, n)` | |
| items | `give_item(p, section [, n])`, `inventory(p [, source])`, `count_item`, `dump_inventory(p, tag [, source])` | source `online` (id/section/slot, equipped slot via item_in_slot) or `server` (parent scan, works on the dedicated server) |
| spawn | `spawn(section, where, opts)`, `spawn_npc(section, {near, offset, relation})`, `remove(id)` | relation friend/neutral/enemy applied once the NPC is online. **`spawn_npc` returns TWO values, the server object then the id: write `local se, id = L.spawn_npc(...)`** (using the first value as an id fails with luabind "No such operator defined") |
| relation | `set_relation(npc, rel, player)`, `get_relation(npc, player)` | `npc` = game_object OR object id; it must be online; `player` = player spec (nil = first player) |
| hits | `hit(target, {who, bone, power, type, impulse})`, ACTION `hits_to_kill{section, id, near, offset, power, bone, who, impulse, max, interval, keep}` | result: `hits, dead, killed, hp0, hp[], hurt_at_start`; see "hits_to_kill" below |
| death | `kill(target, killer)`, ACTION `kill_player(player, killer)` | lethal hit with the killer as attacker, relative-health fallback |
| move | ACTION `teleport(player, pos [, dir])` | teleport_actor_sv on the server, set_actor_position fallback, verifies the position |
| NPCs | `npcs_near(where, radius, opts)`, `dump_npcs(where, radius, tag, opts)` | name, section, alive, online, job (smart terrain), scheme (online), distance |
| travel | ACTION `travel(dest, {timeout, fallback})`, `travel_arrived()`, `guide_code(x)`, `GUIDE`, `ALL_LEVELS` | guide flag + `coop_map_vote.on_yes` for every player every 8 s. Success restarts the VM: call `travel_arrived()` in the next VM |
| save/load | ACTION `save()`, `saves()`, `load_last()` | `game_sv.saveGame` (the server's own save), `game_sv.loadLastSave`; VM restarts after the load. `save()` result is ONE value, the save file name string (`"quicksave - 1.scop"`), or `nil, why` |
| talk | ACTION `open_talk(npc, {shot})`, `close_talk()` | teleports 1.5 m in front, `run_talk_dialog`, checks `is_talking` |
| screenshot | ACTION `screenshot(tag)` | engine screenshot renamed `qa_<tag>__<original>.jpg` |
| language | `language()` | "rus" / "eng" as mounted by the engine |
| places | `PLACES.cordon_fire`, `PLACES.cordon_trader_bunker` | `{x, y, z}` arrays for the rookie village campfire and Sidorovich's bunker |

`where` arguments (`teleport`, `spawn`, `npcs_near`, `dump_npcs`): a plain `{x, y, z}` array, a `vector`, a game_object or server object, an object id
(its server position), or nil (the first player / the local player). Player arguments (`p`, `player`): nil, id, name ("qaa"), object.

### hits_to_kill
`L.hits_to_kill{...}` is an ACTION. With only `section` it SPAWNS ITS OWN target 4 m from the player (it does not hit an NPC you spawned
earlier); pass `id=<server object id>` to hit an NPC you made. Options: `near`, `offset` (spawned target), `power` (0.5518 is about one PM bullet),
`bone` (default `bip01_spine1`), `who` (attacker), `impulse`, `max` (30 hits), `interval` (1.2 s), `keep` (leave the NPC alive afterwards).
Results: `hits` (counted hits), `dead` (target dead at the end, also true when somebody else killed it), **`killed`** (`dead` and `hits > 0`:
assert this one), `hp0` (health before the first hit), `hp[]` (after each hit), `hurt_at_start`.
- A spawned target that is dead or wounded before the first hit (the villagers shoot a hostile bandit beside the fire) is respawned up to 3 times.
- A target that is **already dead before the first hit** ends the action with `nil, "target was already dead ..."` and counts no hit, for `id=` too
  (it is never respawned there). A test must not be able to pass with 0 hits.


### Game language (outside the game): `qa_lang.ps1`
xrMPE picks the language from `HKCU\Software\X-Ray Multiplayer Extension\InstallLang` (eng/rus/ukr) when the client starts its file system
(an addon `localization.ltx` is ignored; trick from `patches\repeatable_quests\NOTES.md`). `qa_lang.ps1` sets it, starts `run_coop.ps1`,
restores the original as soon as the client logged `Init FileSystem` (or after `-HoldSeconds`), always in a `finally` block; the original is
also saved in `slot_state\qa_lang_original.txt` so `qa_lang.ps1 -Restore` repairs a killed run.
```
powershell -NoProfile -ExecutionPolicy Bypass -File qa_lang.ps1 -Lang rus -Owner botlang -Expect 1 `
  -RunCoopArgs "-Map coop_l01_escape -Owner botlang -Mode listen -Clients 1 -Hooks C:\...\my.lua -SoakSeconds 60 -ResultDir C:\...\res"
```

## Smoke run
`lua/qa_lib_smoke.lua`, Cordon, listen mode, one client (about 10 minutes with the two level changes):
```
powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner botlib -Mode listen -Clients 1 `
  -Hooks C:\...\tools\stalker_xrmpe\lua\qa_lib_smoke.lua -SoakSeconds 600 -CompareTimeout 10 -ResultDir <dir>
```
`-Cfg parts=base,npc,hits,talk,save,travel,death` runs a subset (one `-Cfg` per run: run_coop takes a single value through `-File`).
Regression run of the 1.2 fixes (`lua/qa_lib_regress.lua`, Cordon listen mode, about 3 minutes): `run_coop.ps1 -Map coop_l01_escape -Owner <unique> -Mode listen -Clients 1
-Hooks ...\lua\qa_lib_regress.lua -SoakSeconds 150 -CompareTimeout 10 -ResultDir <dir>`, then `python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix RG --require 8`.

## Proven in the game (Cordon, listen mode, one client)
Run `results\botlib_smoke5` (2026-10-21, `run_coop.ps1 -Mode listen -Clients 1`, lane copy, soak 540 s): **41 PASS, 0 FAIL** assert lines in `qa_assert.log`.
The `RESULT: FAIL` that run_coop prints for this run is only the known harness noise after the respawn and the level change ("A sees player id ... that no client reports"); shared state was equal (level, flags, infos, tasks).

Timings from `qa_events.log`: Cordon part (base, npc, hits, talk, screenshot, save) done 93 s after the spawn; travel to Garbage through the guide flag, the vote `on_yes` calls and the fallback teleport **70 s**; the engine autosaves on every level change, so `load_last` loads the newest save (the one `L.save()` made on Garbage). Death test: the player respawned through the harness.

```
PASS QL player() finds the local player 12950
PASS QL local_player() and level_name() coop_l01_escape
PASS QL state_set / state_get alpha 7
PASS QL flag_give sets the shared story flag 
PASS QL flag_clear clears it 
PASS QL info_give / info_has (per-player info portion) players given 1
PASS QL info_clear removes it 
PASS QL set_money 1234
PASS QL give_money (delta) 1000
PASS QL give_item creates server objects 2
PASS QL dump_inventory (server scan) lists the 2 medkits medkits 2, items 7
PASS QL dump_inventory (online walk) lists the medkits and slots source online, medkits 2, equipped 5, items 8
PASS QL count_item 2
PASS QL language() reads the mounted language eng (WINDOWED)
PASS QL spawn_npc creates the bandit 13139
PASS QL spawned NPC comes online 
PASS QL spawn_npc relation=friend applied (relation() reads friend) friend
PASS QL some friend call makes relation() read friend friend
PASS QL set_relation enemy and read back enemy
PASS QL engine health setter is RELATIVE (x adds x; applied on the next frame) 1.000 -> same frame 1.000 -> 2 s later 0.802
PASS QL set_health sets an absolute value (read 2 s later) 0.602
PASS QL heal / positive x adds (capped at 1) 1.000
PASS QL npcs_near lists NPCs around the player (name/section/job/scheme) 207 NPCs within 250 m, 201 with a smart-terrain job
PASS QL hits_to_kill (body, PM-sized hits) kills the bandit 3 hits (hp0 1.00)
PASS QL hits_to_kill (head) kills the bandit 1 hits (hp0 1.00)
PASS QL teleport moves the player to the trader bunker teleport_actor_sv
PASS QL open_talk opens the Sidorovich window (is_talking) is_talking=true, shot qa_smoke_talk__ss_<user>_10-21-26_01-49-51_(coop_l01_escape).jpg
PASS QL close_talk closes the window false
PASS QL screenshot is taken and tagged qa_smoke_tag__ss_<user>_10-21-26_01-49-56_(coop_l01_escape).jpg
PASS QL save() writes a save file the way the server does quicksave - 1.scop
PASS QL travel arrived on Garbage after the party vote coop_l02_garbage in 70 s
PASS QL save() on the new level quicksave - 2.scop
PASS QL flag cleared before the load 
PASS QL load_last: newest save (made on Garbage) is loaded coop_l02_garbage
PASS QL load_last: the flag cleared after the save is back (state restored from the save) 
PASS QL load_last: the flag set on Cordon before the first save is still there 
PASS QL death: killer NPC spawned 
PASS QL death: killer is online 
PASS QL kill_player kills the player with the NPC as attacker hit
PASS QL player respawns after the death (harness respawn) 
PASS QL smoke run finished 
```

hits_to_kill (sim_default_bandit_0, power 0.5518): bone bip01_spine1: 3 hits (hp0 1.000); bone bip01_head: 1 hits (hp0 1.000)

Engine facts found while proving the library (all from this run):
- `obj.health = x` is relative and is applied on the NEXT frame: 1.000 became 0.800 after `-0.2`, but a read in the same frame still gave 1.000.
- `npc:set_relation(...)` only changes the personal goodwill; `npc:relation(player)` also adds the community relation, so a bandit still read "enemy" after `set_relation(friend)`. `force_set_goodwill(1000, player)` makes it read friend; `L.set_relation` does both.
- `coroutine.create/resume` hard-crashes LuaJIT in this engine (`lua_getinfo` in the stack, `results\botlib_diag1`): qa_lib uses action tables instead.
- A hostile bandit spawned beside the Cordon village is often killed by the villagers before the first hit (hp0 -1 seen); `hits_to_kill` respawns a spawned target up to 3 times and fails (never "0 hits, dead") when it stays dead.
- The guide travel needs the game clock: the guide restrictor teleports the party after `on_game_timer = 20`; `L.travel` sets `level.set_time_factor(300)` and, with `fallback`, teleports to `esc_smart_terrain_1_guide_temp_<N>_walk/look` itself after 40 s (N per destination: gar 1, agr 2, agru 3, val 4, x18 5, bar 6, ros 7, yan 8, x16 9, mil 10, rad 11, x10 12, pri 13, aes_1 14, sar 15, con 16, aes_2 17).
- Every player death restarts the Lua VM (the harness logs a new `HARNESS start` on the same level). The smoke records its stage before the death test; because its killer bandit is not released (the VM restarted), it kept killing the respawned player and the log shows 5 further restarts that only print "stage 3 already finished".

Language switch (`qa_lang.ps1` + `lua\qa_lib_lang_probe.lua`, run `results\botlib_lang_rus2`, 2026-10-21): `PASS QL language() reports the mounted language want rus, got rus`
(the translated option string came back as the cp1251 bytes `CE CA CE CD CD DB C9`), and `InstallLang` was `eng` again right after
(`language window: 23 s, file system initialised in the run: True`, `InstallLang restored to eng`). qa_lang waits until `run_coop` logs `BUILD_OK`
(it queued 261 s behind other runs without touching the registry) and switches the value a few seconds before the client starts; the client
reads the language a few seconds after its process starts, so the value is restored as soon as `Init FileSystem` shows in the client log.
Another agent that launches a game inside that short window would also get Russian.
