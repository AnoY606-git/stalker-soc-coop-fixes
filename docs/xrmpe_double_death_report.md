# xrMPE 0.9: dedicated-server crash when a player body receives two death events (CEntity::Die twice)

For the xrMPE developers. Written from the Shadow of COOP fix-patch test work (S.T.A.L.K.E.R. SoC co-op add-on, xrMPE 0.9,
engine build 9789 of Nov 26 2025, `xrGame.dll` 7,915,520 bytes). No personal paths or names are in this file.

## 1. Symptom

The dedicated server (and a listen host, same code) closes with an access violation a moment after a player dies, with no Lua error and no
`FATAL ERROR` block. The last two lines of `xray_*.log` before `stack trace:` are the SAME "killed by" line twice:

```
<player> killed by sim_default_bandit_NNNNNN ...
<player> killed by sim_default_bandit_NNNNNN ...
stack trace:
0023:........ VCRUNTIME140.dll, memmove()
0023:........ xrGame.dll, CDialogHolder::UseIndicators()      <- the log names the nearest EXPORT, not a real function
```

A normal death prints that line once. A crash dump shows `EXCEPTION_ACCESS_VIOLATION (0xC0000005)` inside `VCRUNTIME140!memmove`
(a read, page aligned address, `edx = 0xFFFFFFFC`).

Game-side RVAs in `xrGame.dll` (identical in all three crashes below; frames in order, top first):

| RVA | meaning (from the disassembly, see section 4) |
|---|---|
| (memmove) | called with count = end - (it + 4) where `it == end()`, i.e. count = -4 -> `edx = 0xFFFFFFFC` |
| `0x315ED7` | `CGroupHierarchyHolder::remove_from_group(CEntity*)`: `std::find` then `vector::erase(it)` with `it == end()` |
| `0x285F7B` | `CEntity::Die`: sets health -1, clears the registered flag, calls `remove_from_group` |
| `0x289AE9` | caller of `Die` (event handler for GE_DIE, `CEntityAlive::OnEvent`) |
| `0x12D00B`, `0x2864A8`, `0x1463E0`, `0x14B5E0`, `0x35152B`, `0x3500D6` | net event dispatch, `CLevel::ProcessGameEvents` up to the frame loop |

## 2. Three occurrences (event sequence)

All three are the same pattern: the actor body is killed, and the engine delivers GE_DIE for that body a second time in the same event pass.

**A. Maintainer's dedicated server, real play (Cordon, 1 player, about 119 hostile squads tracked).**
1. quest taken, quick save (`game_sv.saveGame`, "13787 objects are successfully saved", `quicksave - 1.scop`) shortly before the fight;
2. firefight with several bandits; the player kills one bandit, other NPCs kill each other around him;
3. `<player> killed by sim_default_bandit_010275 ...` printed twice;
4. `stack trace:` memmove / `xrGame.dll+0x285F7B` ... and the server process is gone.
No save is LOADED in that server log before the death. The client log ends with the same two lines and then "A problem occurred /
Connection dropped" (the client is only a casualty).

**B. Our automated run with repeated save / load (dedicated server, 1 client).**
1. test bot kills the player with a spawned bandit, `game_sv.loadLastSave`; the saved player body stays in the world with nobody controlling it
   (`actor_the_main_character`, the body the engine does not hand back after a load) and the client reconnects as a NEW body;
2. 5th life after the loads: `[PSCALE] restored 108 scaled squads ... from the save`, then at once
   `qaa killed by sim_default_bandit_113569 ...` twice, `stack trace:` memmove, same RVAs. One crash in about 30 deaths of that run.

**C. Deterministic reproduction (this report, live console on a dedicated server).**
The test script applies FOUR lethal `hit` objects (`fire_wound`, power far above the player's health, attacker = a spawned bandit) to the
player body in ONE Lua call, i.e. in one server frame (`game_object:hit()` queues the hit, the engine applies it on the next frame).
- Life 1 (control, single hit): normal death, one "killed by" / "dies himself" line, respawn, no crash.
- Life 2 (4 hits in one frame): the log gets `qaa killed by sim_default_bandit_113578 ...` TWICE, then `stack trace:`, the process is gone,
  the dump has the same RVAs and `edx = 0xFFFFFFFC`.
- The same 4-hit call crashed the server again in a second, fresh session (2 of 2).
- The same sessions survived 12 other deaths by single lethal hits and by 3 AI bandits shooting the player (single "killed by" line each).

Counts of the test work behind this report (6 dedicated live sessions on Cordon, 17 player deaths in total):
- 4 hits in one frame, attacker = bandit: 2 sessions, 2 server exits at that call. Session 1 left a dump with the RVAs above and the
  double "killed by" line; session 2 exited at the same call but its dump and the last log lines were not kept, so it is counted as
  "server gone at the trigger", not as a second identical stack.
- 12 deaths by ONE lethal hit per frame (scripted) or by 3 AI bandits shooting: 0 crashes, one "killed by" line each.
- 2 deaths by two hits in two different frames (10 s apart): 0 crashes.
- Not run (the PC ran out of commit headroom, see section 6): k = 2 in the same frame, `game_object:kill()` twice, explosion and mixed
  damage types in one frame. They are in `tests\death_double_hit` (`dd_only=...`) for whoever runs the next session.

## 3. Cause

The player body gets two GE_DIE events. The first `CEntity::Die` removes the body from its `CGroupHierarchyHolder` (team / squad / group
member list) and clears its registered flag; the second `CEntity::Die` removes it again without looking at the flag, `std::find` returns
`end()` and `vector::erase(end())` moves `-4` bytes: access violation.

Why two events (inferred from the reproduction, not from the engine source): the hits queued for one frame are applied in order inside one
event pass; once the first hit takes health to 0 or below, the following hits of the same pass are still applied to the already dead
body and each one queues its own GE_DIE (the "killed by" line is printed once per GE_DIE). So a burst of two or more hits that includes the
lethal one, in the same server frame, is enough (one hit per frame never crashed). In real play
that is automatic fire from several NPCs (or shotgun pellets) hitting a player on a slow server frame (the maintainer's server had over 100
simulated squads). Nothing in the Lua API can order the hits of one frame, and the engine gives scripts no hook before a player body is hit:
`set_callback(callback.hit, ...)` on the player body never fired in any of the AI or scripted deaths of this test (NPC bodies do get
it, see `coop_balance.script`).

## 4. Disassembly of `CEntity::Die` (xrGame.dll, image base 0x10000000 as loaded in the tool)

```
10285f1c  mov eax,[esi+0x200]
10285f22  mov dword [eax+4],0xBF800000        ; health = -1
10285f29  mov ecx,[g_pGameLevel]
10285f31  call 0x1034fc80                     ; IsGameTypeSingle()-like check on the level
10285f38  je   0x10285f7b
10285f3a  push [esi+0x214]                    ; team
10285f40  mov byte [esi+0x232],0              ; registered_member = false   (written, NEVER read before)
          ... team(..).squad(esi+0x218).group(esi+0x21C)
10285f76  call 0x10315eb0                     ; CGroupHierarchyHolder::remove_from_group(this)
10315ec2  call 0x10576280                     ; std::find(begin, end, member)
10315eca  lea  edx,[eax+4] ; sub ecx,edx ; push ecx,edx,eax ; call 0x105769ac   ; erase: memmove(count = end - (it+4))
```
When `it == end()` the count is `end - (end + 4) = -4`. In this build the byte at `+0x232` is cleared but never tested before the removal,
so a second `Die` on the same body removes it a second time.

## 5. Suggested engine fix (any one of these is enough; the first is the correct one)

1. In `CEntity::Die`: `if (m_registered_member) { m_registered_member = false; ...remove_from_group(this); }`.
2. In `CGroupHierarchyHolder::remove_from_group`: `auto it = std::find(...); if (it == m_members.end()) return; m_members.erase(it);`
   (also fixes any other double removal).
3. Do not queue GE_DIE for a body that is already dead: in the hit path `if (!g_Alive()) return;` before `KillEntity`, or in the GE_DIE
   handler return when the body is already marked dead (`Die` sets health to -1, so `GetfHealth() <= -1` is a cheap test).
Also worth a look: two GE_DIE for one body also give two `OnPlayerKilled` (two kill messages, kill statistics counted twice).

## 6. What a script (Lua) can do

Nothing that could be proven. Reasons, all from the tests above and the disassembly:
- The second GE_DIE is queued inside the same event pass as the first. A Lua call (`level.add_call`, 1 per frame) cannot run between
  them, and no Lua call re-registers a body in its `CGroupHierarchyHolder` (`change_team` removes and adds once, and with equal values does nothing).
- There is no script hook before the hit is applied to a PLAYER body (`callback.hit` never fired, NPC bodies do get it). So the
  "count the hits of this frame and block the second one" guard cannot be written.
- The only script lever left is a floor guard: poll the body every frame and, when health is at or below a floor F, set
  `invulnerable(true)` and `kill()` once by script. It only helps when the burst starts inside the zone below F in a frame, it makes
  every player die at F instead of 0 (a gameplay change, a medkit at 10 percent health would no longer save anybody), and for a burst
  from full health it does nothing. It was written as `tests\death_double_hit\dd_guard_floor_EXPERIMENT.lua` but NOT run in the game
  and NOT shipped: the host PC had 1 to 5 GB of commit headroom for the last 90 minutes of the work (the house rule needs 9 GB before a
  game launch), so no "harmless" and "effective" proof could be made. Do not ship it as a fix.
So the fix has to be in the engine (section 5); Shadow of COOP cannot work around it from Lua.

## 7. How to reproduce (about 2 minutes)

Dedicated server and one client on Cordon. In the server's Lua, on a living player body `po` and a spawned bandit `n`:
```lua
for i = 1, 4 do
  local h = hit()
  h.draftsman = n
  h.type = hit.fire_wound
  h.direction = vector():set(0, 0, 1)
  h:bone("bip01_spine")
  h.power = 300
  h.impulse = 10
  po:hit(h)
end
```
All four calls run in one frame; the server dies on the next frame with the log lines of section 1. With a single call (or with the
calls spread over frames) the player simply dies.
