# CNPP-1 camera shake (patch cnpp_shake)

## v1.4.3: no shaking at all (maintainer FOSTER: "remove the shaking at the NPP")
What shook the camera: the restrictor `aes_1_zone_space_restrictor` of `coop_l11_stancia_1` called `xr_effects.stc_surge` as soon as a player was inside it
(`on_player_inside = {-CON_TEST_1_INFO} sr_idle@nil %=stc_surge%` in the mod). `stc_surge` adds the camera effectors `shell_shock.anm` and `earthquake_00.anm`, the looping
post-process `surge_shock.ppe`, the weather effect `fx_surge_day_3_stancia` and the sound `blowout_begin`. The mod never called `stc_stop_surge`, so it never ended (the post-process loops). v1.4.2 of
this patch made it 15 s of shaking, 45 s calm, repeating.
The original has no constant shaking on this level. Its only shaking is a one-off scripted story event, the timed emission of the assault: after the party starts along the road a
6-minute countdown runs (restrictor `aes_space_restrictor_timer`, `st_time_till_surge`), `xr_effects.start_small_reject` (weather `surge_day`, `vibros_p.ppe`, `aes_earthshake`) fires when the road is entered and at
3, 2 and 1 minute left, and `start_full_reject` at 20 s left (checked in the Steam SoC `l12_stancia` level.spawn and scripts). The mod does not have that event
(no countdown, no `aes_timer_*` flags; see soc_aes_military NOTES) and it is NOT added here: the request was to remove the shaking, and a timed emission nobody asked for would be new
gameplay on a level where players take their time. The mod's `stc_surge` is not a copy of it (different effectors, looping, no countdown, no end).
Nothing else on CNPP-1 / CNPP-2 shakes the camera (searched the mod's scripts and configs for `add_cam_effector`, `add_pp_effector`, `set_weather_fx`, `stc_surge`: only
`xr_effects.stc_surge`, and the Sarcophagus psi field `sar_psi_radiotion_30` of `sr_psy_antenna`, which is another level and as in the original; `coop_l11_stancia_2` has only particle effects).
Change: `gamedata\configs\scripts\coop_l11_stancia_1\space_restrictors\aes_1_zone_space_restrictor.ltx` starts in the empty section and never calls `stc_surge`. The old section names
(`start_surge_idle`, `surge_on`, `surge_off`) stay because a save made with v1.4.2 or earlier stores the active section by name: they go to the empty section and call `stc_stop_surge` once,
which removes the camera effectors and the post-process on the client (it does nothing without a local actor, i.e. on a dedicated server). So a running game that was loaded in the shaking state
is cleaned up on load. `xr_effects.dscript` is not changed (it also holds `task_guard`; `stc_surge` is simply not called any more).
Not run in the game (offline work): the file is a plain config; the section names and keys are the ones of the old file.

## v1.4.2 (kept for the history)
`stc_surge` / `stc_stop_surge` do nothing without a local actor (the dedicated server raised an error every wave), remove every effector before adding it again, the two camera effectors have their own ids
(20080501 and 20080503) and `surge_shock_pp_eff` is defined. The `task_guard` block at the end of `xr_effects.dscript` belongs to patch `task_guard`.

## Кратко по-русски
ЧАЭС-1: тряска камеры убрана совсем. Её запускал рестриктор зоны уровня (`stc_surge`: камерные эффекты shell_shock и earthquake, зацикленный постпроцесс surge_shock); в оригинале на этом уровне тряски нет.
Рестриктор теперь сразу в пустой секции; старые имена секций оставлены ради сохранений (они один раз вызывают `stc_stop_surge` и убирают эффекты). Игру не запускали.
