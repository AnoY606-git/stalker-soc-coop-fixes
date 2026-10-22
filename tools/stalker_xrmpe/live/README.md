# Live console and ready-made saves for Shadow of COOP (xrMPE 0.9)

Ask a running game questions instead of writing a hook and a whole `run_coop` for each one.
`start_live.ps1` boots a harness slot and leaves it running; `lua.ps1` sends Lua into the server or a client and prints the answer in
about 0.2 to 0.7 s; saves put you in Bar, Agroprom, X18 or the Sarcophagus without driving there.
Everything here only ADDS files. `run_coop.ps1` / `stalker_slot.py` behave as before (the one change is an opt-in `-Save` flag on `run_coop.ps1`).

## Quick start
```
cd <repo>\tools\stalker_xrmpe\live
powershell -NoProfile -ExecutionPolicy Bypass -File start_live.ps1 -Map coop_l01_escape -Owner me -Name me
powershell -NoProfile -ExecutionPolicy Bypass -File lua.ps1 -Name me "live.state()"
powershell -NoProfile -ExecutionPolicy Bypass -File lua.ps1 -Name me "live.count(live.find('esc_campfire',1)[1].pos, 25, 'stalker')"
powershell -NoProfile -ExecutionPolicy Bypass -File stop_live.ps1 -Name me
```
- Use your own `-Owner` and `-Name` (they must be unique per person: the owner is the slot lease name, the name is the state file).
- `-Save bar_arrival` starts in the Bar from a save (`-Map` is taken from the save). Add the same `-ExtraDir` the save was made with (see below).
- `-ExtraDir <stage>\gamedata` packs your patch files into the test db (as `run_coop` does). Do NOT pass the full 97 MB release stage: the 32-bit game
  process fails with "Not enough memory resources". Use `stages\release_v1.3_lite\gamedata` (67 MB, see `stages\release_v1.3_lite\STAGE.txt`).
- `-Mode listen` makes client A the listen server (alife on A, no role S); `-Clients 2` adds client B. Default: dedicated server S + 1 client A.
- Exit codes of start_live: 0 ready, 1 boot failed (logs in `logs\failed_<tag>`), 2 BUSY (no slot / the owner's own game / more than 6 xrEngine),
  3 setup problem (low disk, unknown save, name already in use). It waits for a free slot (`-SlotWait`), refuses to start below `-MinFreeGb` (default 4).
- The lease is 12 h and has no owner pid; it lives while a registered game pid lives. Always `stop_live.ps1` when done (it kills only its own pids,
  keeps logs in `logs\<tag>`, deletes the appdata/fsgame copies, releases the slot).

## lua.ps1
`lua.ps1 [-Role S|A|B] [-Name n] [-Timeout 30] [-Quiet] "<lua>"` or `-File x.lua`. Default role S (dedicated server, has `alife()`), A if there is no S.
Exit code 0 ok, 1 Lua error, 2 timeout (game frozen or loading), 3 no session / role not running.
The chunk is tried as an expression (`return <chunk>`), then as statements, then as `statements; expression`. Globals you set persist
(`bid = live.spawn(...)` then `live.kill(bid)`). `print(...)` output and return values are shown. Protocol: `live_cmd_<n>.lua` in the role's logs folder,
answer in `live_res_<n>.txt`, polled every 250 ms inside the game (`live_hooks.lua`, appended after `qa_harness.lua`).
A level change restarts the Lua VM: the command number is persisted (`live_seq.txt`) and `live.travel` is answered by the new VM.

## Helpers (table `live`, available on every role)
| Call | What it does |
|---|---|
| `live.state()` | level, role, dedicated, alife, players |
| `live.players()` | list of `{id, obj, name, alive}`; `live.first_player()` = "me" |
| `live.find("campfire", limit)` | every object whose name or section contains the text (server: online and offline), nearest "me" first; records have `.id .name .section .pos .dist .online .alive .job` |
| `live.near(pos, radius, filter)` | objects within radius of `pos` (a vector, `{x,y,z}`, id, player name, or `"me"`), sorted by distance with name / section / distance / job. filter: `"stalker"`, `"mutant"`, `"creature"`, `"alive"` or a function |
| `live.count(pos, radius, filter)` | `#live.near(...)`. NPCs walk and sit down, so a count and a later list are different snapshots and can disagree (11 then 8 at the rookie fire) |
| `live.census(pos, radius, filter)` | count AND list from one scan: the header says `[N result(s)] (snapshot at game time ...)`, then one line per object. Use it when the two numbers must match |
| `live.tp(x, y, z [, who])` | move every alive player (or `who` = name/id) with the mod's own `teleport_actor_sv`, then WAIT until the position really changed and report where each player is now (or `NOT MOVED: ...` with the reason after 10 s). Server only. Fixed 2026-10-21: it used `set_actor_position`, which printed success and moved nothing |
| `live.spawn("section" [, pos])` | `alife():create` on a valid AI-mesh vertex 4 m in front of "me"; returns the entity id. Server only. Section example: `sim_default_bandit_1` |
| `live.peace()` | make NPC communities and the players neutral, so a spawned bandit is not shot by the village before you test on it (valid community names only: an unknown one asserts and kills the server) |
| `live.hit(obj, power [, bone [, type]])` | one hit; `type` wound (default) / fire_wound / strike / explosion. The engine applies it on the NEXT frame |
| `live.kill(obj [, power [, bone [, type]]])` | one hit per frame until dead; the answer says "dead after N hits". `wound` and `strike` leave a stalker at about 0.1 health: use `fire_wound` |
| `live.shot("name")` | engine screenshot on a client (`-Role A`); lua.ps1 copies it to `shots\name.jpg` |
| `live.inv([player])` | inventory of the player (section x count, money) |
| `live.travel("bar")` | from Cordon: gives the guide flag and votes yes for every player every 8 s; codes AES_1 AES_2 AGR AGRU BAR CON GAR MIL PRI RAD ROS SAR VAL X10 X16 X18 YAN. The answer comes after the level change ("arrived on ... after N s") |
| `live.save()` / `live.load_last()` | the server's own save / load newest save (use `save_live.ps1` for the file) |
| `live.reload("name" [, path])` | re-run a script file into the namespace of the loaded script `name`, no restart. Without `path` it looks for `<name>.script` / `.dscript` in the `scripts` folder of each `-ExtraDir` |
| `live.async(step, timeout)` | return this from a command: `step()` runs every frame until it returns a value, which becomes the answer |
| `live.defer(sec, fn)`, `live.note(text)` | run later from the poll loop; append to `live_notes.log` |

### Reloading scripts, and what needs a restart
`live.reload` re-executes a script file in the namespace table of the already loaded script: functions and tables assigned at file level are replaced for every
caller that looks them up through the namespace (`coop_scenes.status()`), `local` variables and local functions of the old file are not touched and old
upvalue state stays. Typical loop: edit `<stage>\gamedata\scripts\x.script`, `lua.ps1 "live.reload('x')"`, call the function again.
**ltx / xml / spawn / level / texture changes need a restart** (the engine reads configs and archives once). A syntax error in the file is reported and nothing changes.

## Saves
`saves\<name>.scop` + `.json` (level, the stage it was made with, date, note). Applied by `start_live.ps1 -Save <name>` into the server's appdata as
`savedgames\<addon>\<level>.scop`: the dedicated server starts `server(<level>/coop/...)` and loads that file when it exists ("Cannot find saved game ..." in the log means it did not).
The same file works with `run_coop.ps1 -Save <name>` (opt-in; adds `live_hooks.lua` and `live_save=1`; default behaviour unchanged).

| Save | Level | Made how | Time it took | Size |
|---|---|---|---|---|
| `cordon_start` | coop_l01_escape | fresh Cordon start, saved after `coop_scenes` intro + Sidorovich intro were played, player in the bunker | boot 72 s, save 1.6 s | 603 KB |
| `bar_arrival` | coop_l05_bar | from a session started on `cordon_start`: `live.travel('bar')`, saved on arrival (alife online, 34 stalkers within 60 m) | vote to arrival 71 to 74 s | 644 KB |
| `agroprom` | coop_l03_agroprom | same, `live.travel('agr')` | 24 s | 618 KB |
| `x18_entrance` | coop_l04_x18 | same, `live.travel('x18')`; the arrival point is the entrance | 20 s | 631 KB |
| `sarcophagus` | coop_l11_sarcofag | same, `live.travel('sar')`; Monolith, door and decoder as on arrival | 27 s | 641 KB |

**Stage of every save: coop.addon + `-ExtraDir live\stages\release_v1.3_lite\gamedata`** (the v1.3 release stage built by
`build.py --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry`, without textures). A save only loads with the same stage (all.spawn and script state);
remake with `make_saves.ps1` (all five, one live session each) after a stage change. `save_live.ps1 -As <name> [-Note text]` saves the running world; `verify_saves.ps1`
loads each save and checks level, alife and a stalker count.

Verified loads (each in a live session, level + alife + stalker count; `verify_result.txt`, `verify_saves.ps1`): cordon_start (player moved to the bunker, intro already played),
bar_arrival (34 stalkers within 60 m, 76 to 97 s to READY), agroprom (6 within 80 m), x18_entrance (86 within 80 m, server queries only: no respawn point for new players), sarcophagus (67 within 80 m; the
saved actor is dead in that save, the loaded world is the Sarcophagus after arrival).

Things to know about a loaded save:
- The saved actor ("ghost", `actor_the_main_character`, id 13056) is brought back standing in the world, and the real harness client spawns as a new player in the **lobby box**
  (105, -15.8, -10), where `set_actor_position` does not move it. `live.first_player()` ("me") therefore picks the player that is not in the lobby, so `live.near('me', ...)` queries the world.
- The harness' own respawn would never spawn the client (the ghost counts as an alive player), so in save mode `live_hooks` respawns spectators until all clients exist.
- `run_coop -Save` compare shows `MISMATCH [presence] A sees player id 13056 that no client reports as itself`: that is the ghost, not a bug.
- Levels without a respawn point for NEW players (X18 seen): the loaded world answers, but the client never becomes a player. `start_live -Save` then prints `WARNING: client(s) A did not spawn ...` after `-SpawnGrace` (120 s) and still returns READY; use role S.
- `live.count` / `live.near` on the server count server entities, online and offline (alife); filter with `function(r) return r.online end` for what is actually loaded around the player.
- The lobby overlay (READY, character select) is native UI and stays on screen, but after `live.tp` the camera is at the new spot, so `live.shot` shows that place behind the overlay (checked 2026-10-21). Server-side queries do not depend on the screen.

## Demo transcript (2026-10-21, `demo.ps1`, real wall-clock times)
(Correction: the `live.tp` line in this transcript printed success but the old code moved nobody. The current `live.tp` was re-checked on a fresh Cordon session: 1 player moved to the target in 0.0 s, the client's real player object and camera followed, and a screenshot showed the new spot behind the lobby overlay.)
The PC was heavily loaded by other agents' test runs (5 to 11 xrEngine processes, almost no free RAM), so every wait below is a worst case: start-up of PowerShell alone takes 2 to 3 s per command here;
the game itself answers in 0.2 to 0.7 s (`lua.ps1` prints that round trip without `-Quiet`; on a quiet PC the whole `lua.ps1` call is about 1 s).

```
[02:11:17] start_live.ps1 -Map coop_l01_escape                      (Cordon, fresh start)
           slot wait 132 s, lane build 163 s (both caused by the load; 1 to 5 s on a quiet PC)
[02:18:24] LIVE READY in 126 s (dedicated server up after 21 s, client A after 27 s)      -> Cordon live ready 428 s after the call
[02:18:25] 1. live.count(live.find('esc_campfire',1)[1].pos, 25, 'stalker')   -> 7        (6.4 s wall clock; list of the 7 with job kamp/walker follows, 4.5 s)
[02:18:40] 2. live.peace(); bid = live.spawn('sim_default_bandit_1'); live.kill(bid, 0.02, nil, 'fire_wound')
                                                                     -> dead after 53 hits (0.7 s in game, 3.4 s wall clock)
[02:20:00]    (the Sidorovich intro scene of a fresh start puts players back in the bunker: waited 72 s for coop_scenes.status() = active=nil)
[02:20:00] 3. live.tp(-206,-19.6,-130)  -> 1 player(s) moved                                (3.3 s)
[02:20:03]    live.shot('demo_cordon_fire') (-Role A) -> screenshot saved to live\shots\demo_cordon_fire.jpg   (3.7 s; lobby overlay, see above)
[02:20:07] 4. live.inv()  -> inventory of qaa: 5 items (bolt, device_pda, device_torch, wpn_binoc, wpn_knife), money 0   (3.8 s)
[02:20:11] 5. coop_scenes.status()                                  -> active=nil queue=0 installed=true
           live.reload('coop_scenes', 'demo\status_patch.lua')      -> reloaded coop_scenes ... (2.7 s)
           coop_scenes.status()                                     -> PATCHED by live.reload: coop_scenes.status() now answers from the reloaded file
[02:20:33] stop_live.ps1 -Name lcdemo                                (slot released)
[02:20:33] start_live.ps1 -Save bar_arrival                          (Bar, alife online)
[02:25:56] Bar live ready 323 s after the call (slot wait 67 s, lane build about 3 min under load, boot 77 s of it)
[02:25:56] live.state()                  -> level=coop_l05_bar server=true dedicated=true alife=true players=[actor_the_main_character#13056, qaa#16128]
[02:26:02] live.count('me', 60, 'stalker') -> 34                  (3.0 s wall clock, 0.35 s in game)
[02:26:04] live.near('me', 40, 'stalker')  -> 10 stalkers/duty with job (animpoint, walker, kamp), nearest 13.5 m: sim_default_stalker_3 job animpoint@bar_smart_terrain_7_animpoint_2 ...
```
Full text with every line: `demo_transcript.txt`.

### Time to answer versus a normal `run_coop`
Same question, "how many stalkers stand within 60 m of the Bar arrival point", through `run_coop.ps1 -Map coop_l05_bar -Save bar_arrival -Hooks demo\bar_census_hook.lua -SoakSeconds 10 -CompareTimeout 10`
(`logs\normal_run_bar\run.log`): server started 02:08:29, client A spawned after 118 s, `RESULT` printed at 02:10:51 = **142 s after launch**, answer n=25 (the hook counts section names containing "stalker"; the live query counts the stalker class incl. Duty: 34).
The hook has to be written, built into the addon (4 s on a quiet PC), the slot taken, and **every new question means a new run**: a second question costs another 140 s plus the slot wait.
In the live session the Bar is already loaded: the first answer comes 77 to 97 s after `start_live -Save bar_arrival` (boot) and the second, third and tenth question 0.2 to 0.7 s each.
Without the save, getting to the Bar means a Cordon boot (72 to 97 s) plus the vote (71 to 74 s) in every run.

| | normal run_coop | live console |
|---|---|---|
| first answer, Bar | about 142 s after launch + writing the hook | 77 to 97 s boot with `-Save bar_arrival` |
| next question | another full run, 140 s+ | 0.2 to 0.7 s |
| Cordon -> Agroprom / X18 / Sarcophagus | boot + vote (24 / 20 / 27 s) every time | a save, or `live.travel` once |
| change a function and try again | rebuild + new run | `live.reload`, about 1 s |

## Files
`start_live.ps1`, `stop_live.ps1`, `lua.ps1`, `save_live.ps1`, `make_saves.ps1`, `verify_saves.ps1`, `demo.ps1`, `live_hooks.lua`, `saves\`, `stages\release_v1.3_lite\`, `demo\`, `state\` (session json, deleted by stop), `logs\` (kept logs of stopped sessions), `shots\`.

## Limitations (known, with the reason)
- Needs a free slot and a quiet enough PC: under the 2026-10-20 load a start took 5 to 7 minutes before the boot even began (slot queue, more than 6 xrEngine wait, lane build).
- Screenshots always carry the lobby overlay (READY is native UI); the world is visible behind it after `live.tp`. All world questions are answered server-side.
- On a client, `db.actor` is a DUMMY (id 0, name `actor`, it never moves). The real player object is `live.first_player().obj` (id from `LocalActor()`): use that for client positions.
- `coop_scenes` (cutscene queue, used in the `live.reload` example) only exists when the session was started with the lite stage (`-ExtraDir stages\release_v1.3_lite\gamedata`); a plain `start_live` has no such script and `coop_scenes.status()` says `attempt to index global coop_scenes`.
- Disk: `start_live` stops below `-MinFreeGb` (default 4) and prints a WARNING below 10 GB (house rule: keep 10 GB free); use `-MinFreeGb 10` to make 10 GB a hard stop. A session costs tens of MB.
- Saves load only with the exact stage they were made with. A boot with the full 97 MB release stage fails (32-bit address space); use the lite stage.
- `live.spawn` / `live.hit` / `live.kill` need an online object (near a player); `live.peace` changes relations for the whole session.
- `live.reload` cannot touch `local` state of the old file; configs need a restart.
- `game_sv.saveGame` writes `quicksave - N.scop` (rotating 1 to 5): `save_live.ps1` copies the file that changed.
