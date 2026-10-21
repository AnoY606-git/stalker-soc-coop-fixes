# Gray / Garbage hangar "Total Lawlessness" (Полный беспредел): bandits stay passive (code-only, UNTESTED in game)

Cause (static): `gar_the_order_to_kill_gray_space_restrictor.ltx` gives `+GAR_THE_ORDER_TO_KILL_GRAY_INFO` with `on_actor_inside`, which tests
only `db.actor`. Every bandit (`gar_smart_terrain_6_walker_bandit_*`) sits in `..._idle` with `combat_ignore_cond = true` until that info exists
(`on_info = {+GAR_THE_ORDER_TO_KILL_GRAY_INFO} ..._attack`), so for a joined client the attack never starts. Gray stays `meet = no_meet` until
both bandit squads are dead (`animpoint ..._1` has `meet = meet`), which matches "can only talk to Gray after killing everyone".

Fix 1 (v1.3): `on_actor_inside` -> `on_any_player_inside` (any connected player entering starts the fight). Gray's later dialog is global
story-flag based (dialogs_coop_l02_garbage.xml, flag GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO), so any player can talk once both
bandit squads are dead.

## Update 2026-10-21 (FOSTER, v1.4): the bandits still stand far away and the two groups only look at each other; the SoC group had about 6 bandits
FOSTER's screenshot (right after the task "Total Lawlessness" was completed): the spot by the road with the concrete blocks next to the hill.
* The info only came from the restrictor on top of the hill (-103.5, 10.4, -1.5, a zone players rarely enter), 50 m from the bandits and 40 m from Gray's
  stalkers, and the sections after the info only kept every NPC on its post (the same path point, no movement). Nothing started the fight unless a player
  stepped on the hill.
* SoC reference: smart terrain `gar_seryi_bandits` (-113.9, 0.4, 11.9): SIX bandits `gar_bandit_seryi_1..6` stand 1 m apart at the foot of the hill, Seryi
  (Gray) with 2 companions in the hangar (`gar_angar`, -59, 0.6, 11). The mod's smart terrain 6 has five jobs: four at the same spot, one (`walker_1`) on a
  post at (-194.6, 7.8, 7.7), 80 m west, that nobody sees from the hangar.

Changes
| File | Change |
|---|---|
| `garbage_duty\...\coop_scn_garbage_duty.script` | the server (2 s tick) gives `+GAR_THE_ORDER_TO_KILL_GRAY_INFO` as soon as any alive player is within 60 m of Gray's hangar post (-63.7, 0.8, 8.4), so the fight starts when somebody can see it and Gray's stalkers do not die unseen (project decision; an earlier draft gave the info with the task). The info is a saved, synced story flag. The hill restrictor stays as a second trigger. |
| `gar_smart_terrain_6_walker_bandit.ltx` (here) | six jobs (was five). Idle spots, all existing paths of `gar_smart_terrain_6` (a job can only use paths of its own smart terrain): `walker_2..5_walk` as before, `walker_1` moves from the far post to `walker_3_look` (-113.4, 0.5, 14.7), the new `walker_6` stands on `walker_4_look` (-114.1, 0.4, 4.9): six bandits within 10 m at the foot of the hill, 0.7 to 3 m apart (SoC: 1 m). The attack sections now walk to `walker_2_look` / `walker_5_look` (-70.7, 1.0, 11.5 / 3.9), 7 m from Gray's firing line, in `assault` state, without `combat_ignore`: they advance and shoot at whoever they see (stalkers and players are enemies of the bandit faction). |
| `smart\gar_smart_terrain_6.ltx` (here) | `gar_smart_terrain_6_walker_bandit_6` added to `[exclusive]`. |
| `squad_descr_coop_l02_garbage.ltx` (here, shared file) | `gar_smart_terrain_6_bandit_2_squad` has 3 members (was 2): 3 + 3 = 6 bandits for 6 jobs. Also holds the Duty squad edits of `garbage_duty`. |
| `player_scaling\...\squad_descr_pscale.ltx` | the generated copy `gar_smart_terrain_6_bandit_2_squad_ps` kept in step (3 members). |

Not changed: story ids, flags, `on_death` flags, Gray's and the stalkers' logic (they fight as before once the info exists), `simulation.ltx`, `all.spawn`.

Test plan (single listen host; live console; Garbage by the party vote from Cordon)
1. Count: after level load list objects whose name contains `sim_default_bandit_1` within 25 m of (-114, 0.5, 10): expect 6, positions as above (y 0.4 to 0.6), none near (-194, 7.8, 7.7).
2. Quest: `story_flags.give_flag("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO")` (Bes done), wait 20 s for Gray's message: task "Total Lawlessness" appears and
   `GAR_THE_ORDER_TO_KILL_GRAY_INFO` does NOT exist while every player is farther than 60 m from (-63.7, 0.8, 8.4). Teleport a player to 55 m from it (for example (-118, 0.4, 8) is too close to the bandits, use (-63.7, 0.8, -45)):
   within 2 s the flag exists (`coop_scn_garbage_duty.status()` shows `gray=true`), the bandits are hostile (`npc:relation(db.actor)`), the distance bandit to Gray's
   line shrinks over 30 s, shots are exchanged (health drops on both sides).
3. Finish: kill all six: both `GAR_SMART_TERRAIN_6_BANDIT_n_SQUAD_DEAD` flags, the task completes, Gray talks.
4. Same with a joined client as the only player near the hangar.

## Кратко (RU)
Бандиты Серого теперь нападают, как только любой игрок подходит к ангару ближе чем на 60 м (флаг `GAR_THE_ORDER_TO_KILL_GRAY_INFO` даёт сервер, а не только зона на холме), идут к позиции сталкеров и стреляют; сталкеры Серого не гибнут, пока их никто не видит.
Их шестеро, как в SoC (`gar_seryi_bandits`): у подножия холма у дороги с бетонными блоками (раньше четверо там и один далеко за 80 м). Не проверено в игре.

## Update 2026-10-21 (FOSTER: "do it as in SoC"): the attack starts by the SoC zones
What SoC does (Steam SoC 1.0006: `gulag_garbage.ltx` smart terrain `gar_seryi_bandits`, level.spawn of `l02_garbage`, `xr_effects`): the six bandits `gar_bandit_seryi_*` have
`combat_ignore_cond = {-gar_seryi_open_fire}` (they ignore everybody) and `on_hit` / `on_death` give `gar_seryi_open_fire`; the assault bandit (camper11) has
`on_info = {+gar_begin_assault -gar_seryi_ceitnot} %+gar_seryi_ceitnot +gar_seryi_open_fire%`. Nothing checks a task or the info `garbage_find_stalker` / `garbage_meetstalker_*`:
only the ACTOR ENTERING A ZONE starts it. Three space restrictors of the level do (positions are the same in the mod's Garbage; boxes: centre, full edge lengths, no rotation):
| SoC restrictor | Box | Logic | Effect |
|---|---|---|---|
| `gar_seryi_factory` | 105.48 x 25.59 x 82.39 at (-92.87, 8.67, -1.48): the hill, the bandits, the hangar and Gray's post | `sr_idle`: `on_actor_inside = sr_idle@time %+gar_seryi_actor_enter%`; `sr_idle@time`: `on_timer = 30000 \| nil %+gar_begin_assault%` | 30 s after the first entry the assault starts (the timer runs on even if he leaves) |
| `gar_seryi_igrok_durak_restrictor` ("the player is a fool") | 3.07 x 7.36 x 32.62 at (-76.50, 3.19, 9.90): the strip in front of Gray's firing line | `on_actor_inside = nil %+gar_seryi_open_fire%` | the bandits open fire at once |
| `gar_bandits_shuher` | 33.51 x 19.81 x 82.93 at (-129.37, 5.46, -1.65): the bandits' camp | `on_actor_inside = {-gar_seryi_open_fire} nil %+gar_seryi_open_fire%` | the bandits open fire at once |
Co-op implementation (`garbage_duty\...\coop_scn_garbage_duty.script`, server, 250 ms tick, ANY alive player): the same three boxes, same effects, both mapped to the mod's flag
`GAR_THE_ORDER_TO_KILL_GRAY_INFO` (the bandit sections wait for it): `igrok_durak` or `shuher` -> flag at once; `factory` -> flag 30 s after the first player entered (real time, `time_global`).
The old "any player within 60 m of Gray's post" trigger is gone (it started the fight 30 to 40 m earlier than SoC and from outside the zones).
Fallbacks (cannot soft-lock): (1) the hill restrictor `gar_the_order_to_kill_gray_space_restrictor.ltx` of this patch, now also the SoC way (a player inside, 30 s timer, then the flag; it lies inside `gar_seryi_factory`);
(2) the server tick gives the flag when a player stays within 20 m of Gray's post for 45 s although no zone fired (wrong zone data / different spawn). Both only matter when the first way failed.
Offline: `garbage_duty\tests\zones_mock_test.py` ALL PASS (durak / shuher instant, factory 30 s, timer survives leaving the zone, second player counts, dead player does not, other level nothing).
Not run in the game (offline task).
Кратко (RU): атака бандитов на группу Серого теперь запускается как в SoC зонами уровня: вход в `gar_seryi_igrok_durak_restrictor` или `gar_bandits_shuher` - огонь сразу, вход в `gar_seryi_factory` (большая зона вокруг холма и ангара) - атака через 30 секунд. Любой игрок. Задание и инфо не нужны. Запасные пути: зона на холме (тоже с задержкой 30 с) и 45 секунд рядом с Серым.
