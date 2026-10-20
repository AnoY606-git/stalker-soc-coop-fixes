# CNPP / Sarcophagus lag at the staircase and boss fight (UNTESTED, written from static analysis)

Player report: massive lag and stutters at the end of the CNPP from the staircase on, also in the boss fight. Reloading the
checkpoint cures it for a while, then it returns. Two players, real network.

Owner decision 2026-10-19: no game runs for this patch. Nothing here was run in the game. An earlier in-game attempt only showed
that counts at the spawn point are flat (online objects, alife objects, Lua memory); the test client froze when teleporting, so the
staircase itself was never measured.

## What was checked by reading the scripts and logic files
- Smart terrains of `coop_l11_stancia_1/2`, `control_monolith`, `sarcofag`: no `respawn_params`, `max_population = 1`. The "missing squad"
  restrictors create their squads once (guarded by a `*_STOP_INFO`). No endless respawn.
- `sr_particle` (6 psi antenna generators in CNPP-2, mode 2, looped): one `particles_object` per waypoint, restarted only when
  `playing()` is false. Bounded.
- `xr_sound.set_sound_play`, `sr_teleport`, heli schemes: nothing grows.
- No `level.add_call` is added per update by any CNPP script.

## Findings and changes
1. **Sarcophagus "no gravity" corpses (most likely cause of the continuous lag).** `sar_no_gravity_stalker_monolith_1_1`, `_1_2` and
   `zombied_2_gasballoon_1` switch between two `sr_idle` sections with an unconditional `on_info`, so the section flips on EVERY update
   and runs `hit_obj` (a hit with impulse 3000 on a dead body) every frame, three corpses at once. In multiplayer each hit moves a
   server physics body and is replicated to every client. It only runs while the corpses are online, i.e. when the players come up
   the stairs, and a reload resets the bodies. Fix: `on_timer = 60 |` on the two flips (about 16 hits per second instead of the frame rate).
   Files: `gamedata/configs/scripts/coop_l11_sarcofag/sar_no_gravity_stalker_*.ltx`. If the corpses look different, delete these three files.
2. **CNPP shake (cnpp_shake patch, `xr_effects.dscript`).** `stc_surge` / `stc_stop_surge` now do nothing without a local actor (a dedicated
   server raised an error every wave), remove every effector before adding it again, and the two camera effectors have separate ids
   (20080501 / 20080503; before, the second silently replaced the first). The task_guard block at the end of the file is unchanged.
3. **Not changed, but the real weight of the late CNPP:** CNPP-2 has 54 squads / 149 NPCs, CNPP-1 29 / 101, the Sarcophagus 31 / 86, all with the
   add-on's long sight range. This is steady AI cost that grows as the stairs bring many squads online. The optional `sarcophagus_fps`
   patch addresses it for the Sarcophagus; another agent is lowering the base Monolith count there.

## Player scaling and the Sarcophagus
`player_scaling.ltx` keeps `skip_levels = coop_l11_sarcofag`, so the Sarcophagus is never multiplied by the player count (1.0x for any number of
players), which is within "at most about +0.5x per extra player". Remove it from `skip_levels` only if the base count has been reduced.

## Not tested
Everything. To verify: soak 2 clients on `coop_l11_sarcofag` at the stairs for 3 minutes with `tests` probes (frame time, online objects, Lua KB)
before and after removing the three .ltx files.

## Кратко (для мейнтейнера)
Не проверено в игре. Вероятная причина лага на лестнице Саркофага: три "антигравитационных" трупа (sar_no_gravity_*) каждый кадр получают
hit_obj (переключение секций без условия), в сети это постоянная репликация физики. Добавлен таймер 60 мс. Тряску ЧАЭС (stc_surge)
сделали идемпотентной и только для клиента с актёром. Саркофаг остаётся вне масштабирования по числу игроков (skip_levels).

## Measurement attempt 2026-10-20 (partial, no before/after yet)
Hook: `tests/cnpp_soak.lua` (METRIC line every 10 s per role in `qa_events.log`: frame ms avg/min/max, frames over 50/100 ms, Lua KB,
online objects, alife objects, hit_obj calls, corpse online state and position). Run on `coop_l11_sarcofag` started directly, 1 client,
240 s soak, build WITHOUT cnpp_lag (`build.py --skip=...,cnpp_lag`).
- Server, at spawn point, 300 s: online objects 627 -> 724 (flat after the first minute), alife objects 13085-13094 (flat), Lua KB 32-40 MB
  (slow drift 32 -> 39, not a leak of note), client Lua KB flat 5.5-5.9 MB, client frame 16.6 ms flat.
- The three no-gravity corpses stayed OFFLINE the whole run (hits_ng = 0): the player stood at the spawn point, far from them
  (corpses at about x 11..36, y 63..66, z 44..46; spawn at -31, 0, 43). The teleport step did not run, so the staircase was NOT measured.
- Server frame time was noisy (11 to 30 ms) because other agents had games running on the same PC; do not compare it across runs.
- An earlier 2-client run on Cordon never travelled (client A needed 900 s to spawn under load) and gave nothing useful.
Next: fix the teleport in the hook (use the actor position near y 63, find why `tp_at` never fired on the server role), then run WITH and
WITHOUT cnpp_lag and compare `hits_ng` per 10 s and frame ms.

## Кратко (измерение)
Частичное: на спавне Саркофага счётчики плоские; трупы остались офлайн (hits_ng = 0), лестницу не измеряли. Нужны правка телепорта в
tests/cnpp_soak.lua и два прогона (с патчем и без).
