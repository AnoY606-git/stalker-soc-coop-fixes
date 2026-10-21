# death_double_hit: test hooks for the dedicated-server crash after a player death

Test only, never shipped. Background and results: `docs\xrmpe_double_death_report.md`.

| File | What it does |
|---|---|
| `dd_driver.lua` | Kills the real player again and again with different killers / patterns, keeps its counters in `dd_state.txt` and every step in `dd_events.log` (server `logs` folder, opened and closed per line so a crash loses nothing). Works with or without a Lua VM restart per death. |
| `dd_guard.lua` | Probe: registers `callback.hit` on every player body and logs each call to `dd_guard.log` (found: the callback never fires for a player body). |
| `dd_guard_floor_EXPERIMENT.lua` | An untested idea (invulnerable + one scripted `kill()` when health is at or below a floor). It was NOT run in the game and is not part of any patch: see the report, section 6. |

## Scenarios (`dd_only=<name>` in `-Cfg`, or a line `only=<name>` in `dd_ctl.txt` in the server logs folder)
`plain` (one lethal hit), `multi` (k lethal hits in ONE frame, `k` 2 to 6, `who=npc|self`), `explosion`, `mixed` (four damage types in one frame),
`ai` (3 enemy bandits kill the player), `respawn2` (two hits right after the respawn), `killcall` (`game_object:kill` twice), `killhit`,
`selfonly`, `savekill` (save, then lethal hits 0 to 4 s later), `saveload` (2 bandits, save, load, the next life has the orphan body).
Other keys: `k=<n>`, `who=self|npc`, `powmul=<x>`, `minage=<seconds>`, `noload`, `stop` (pause) in `dd_ctl.txt`.
Default order: a mix of all of them (`ORDER` at the top of the file).

## Run (one live session, dedicated server + 1 client, Cordon)
```
powershell -NoProfile -ExecutionPolicy Bypass -Command "& tools\stalker_xrmpe\live\start_live.ps1 -Name dd -Owner dd -Map coop_l01_escape `
  -ExtraDir @('tools\stalker_xrmpe\live\stages\release_v1.3_lite\gamedata','stalker-soc-coop-fixes\patches\inventory_carry\gamedata') `
  -Hooks @('stalker-soc-coop-fixes\tests\death_double_hit\dd_driver.lua') -Cfg @('dd_only=multi','dd_k=4','dd_who=npc')"
```
(use full paths; `-Hooks` takes full paths.) Watch `dd_events.log`: `DEATH #n done` lines count deaths; when the server process disappears the dump and
`xray_*.log` in the same folder end with the two `killed by` lines. Stop with `stop_live.ps1 -Name dd`.
Before a launch: at most 2 other xrEngine.exe and at least 9 GB of commit headroom.
