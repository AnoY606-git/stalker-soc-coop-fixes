"""Writes the logic files of the six NPCs of patch soc_mil_courier (gamedata\\configs\\scripts\\coop_l07_military\\mil_soc_*.ltx).

Every path is a patrol path that already exists in the mod's all.spawn (the SoC paths of the level kept their points under the mod's names,
see NOTES.md); tools\\check_milc_chain.py proves that every path name used here exists and that no point name has a flag without '='
(utils.parse_waypoint_data aborts on those).  Transitions are driven by story flags that coop_soc_milc.script gives (the server tick), never
by timers or signals of the schemes.

  python gen_logic.py"""
import os

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), 'gamedata', 'configs', 'scripts', 'coop_l07_military')
os.makedirs(out, exist_ok=True)

COMMON = '''meet = no_meet
gather_items_enabled = false
help_wounded_enabled = false
corpse_detection_enabled = false
'''

PAVLIK = '''; patch soc_mil_courier: Pavlik, the snitch of Freedom (SoC mil_Svoboda_stukach, walker0 / walker1 / remark1 of the level.spawn logic).
; Created by scripts\\coop_soc_milc.script. He waits at the SoC wait point (-178.6 -16.9 352.7); when a player comes near the farmstead
; (flag MIL_SOC_COURIER_KHUTOR, the SoC restrictor mil_bandit_restrictor) he walks to the meeting point of the farmstead (the mod's path
; mil_smart_terrain_1_walker_8_walk, the SoC bodyguard point) and stands there looking at the point where the agent arrives.
[logic]
active = remark@mil_soc_pavlik_wait

[remark@mil_soc_pavlik_wait]
anim = guard
target = nil
{common}on_info = {{+MIL_SOC_COURIER_KHUTOR}} walker@mil_soc_pavlik_go

[walker@mil_soc_pavlik_go]
path_walk = mil_smart_terrain_1_walker_8_walk
path_look = mil_smart_terrain_1_walker_8_look
{common}'''.format(common=COMMON)

ARA = '''; patch soc_mil_courier: Ara, the informer (SoC mil_Killer_informator, walker1 / remark1 / walker2 of the level.spawn logic).
; Created when Pavlik has made his call (flag MIL_SOC_COURIER_CALL). He runs along the bodyguard way (the mod's path
; mil_smart_terrain_1_walker_6_walk) to the farmstead; the server tick gives MIL_SOC_ARA_ARRIVE when he is there, then he stands
; and looks at Pavlik; after MIL_SOC_ARA_END he runs out along mil_smart_terrain_1_walker_2_walk (the SoC way out to the west).
[logic]
active = walker@mil_soc_ara_go

[walker@mil_soc_ara_go]
path_walk = mil_smart_terrain_1_walker_6_walk
{common}on_info = {{+MIL_SOC_ARA_ARRIVE}} remark@mil_soc_ara_meet

[remark@mil_soc_ara_meet]
anim = wait_rac
target = story|mil_soc_pavlik
{common}on_info = {{+MIL_SOC_ARA_END}} walker@mil_soc_ara_leave

[walker@mil_soc_ara_leave]
path_walk = mil_smart_terrain_1_walker_2_walk
def_state_moving = run
{common}'''.format(common=COMMON)


def guard(n, way, look):
    return '''; patch soc_mil_courier: bodyguard {n} of Ara (SoC mil_Killer_specnaz, mil_ara_guard{n}). Runs the way to the farmstead, stands
; (guard) when Ara has arrived (flag MIL_SOC_ARA_ARRIVE) and goes back when the talk is over (flag MIL_SOC_ARA_END).
[logic]
active = walker@mil_soc_ara_guard_{n}_go

[walker@mil_soc_ara_guard_{n}_go]
path_walk = {way}
{common}on_info = {{+MIL_SOC_ARA_ARRIVE}} remark@mil_soc_ara_guard_{n}_stand

[remark@mil_soc_ara_guard_{n}_stand]
anim = guard
target = {look}
{common}on_info = {{+MIL_SOC_ARA_END}} walker@mil_soc_ara_guard_{n}_leave

[walker@mil_soc_ara_guard_{n}_leave]
path_walk = mil_smart_terrain_1_walker_1_walk
def_state_moving = run
{common}'''.format(n=n, way=way, look=look, common=COMMON)


COOK = '''; patch soc_mil_courier: the Chef of Freedom (SoC mil_Svoboda_cook, gulag logic@mil_freedom_cook: walker1 with cook_walk1 / cook_look1).
; Sits at his table (the mod kept the SoC points as mil_smart_terrain_11_walker_cook_walk / _look). The talk window gives the SoC cook
; dialogs (small talks, vodka, the Bulldog 6 questions).
[logic]
active = walker@mil_soc_cook

[walker@mil_soc_cook]
path_walk = mil_smart_terrain_11_walker_cook_walk
path_look = mil_smart_terrain_11_walker_cook_look
meet = meet@mil_soc_cook
gather_items_enabled = false
help_wounded_enabled = false
corpse_detection_enabled = false

[meet@mil_soc_cook]
close_snd_hello = nil
close_snd_bye = nil
close_anim = nil
close_victim = nil
far_anim = nil
far_victim = nil
close_distance = 0
far_distance = 0
close_snd_distance = 3
abuse = false
use = {=actor_enemy} false, true
allow_break = true
meet_on_talking = true
'''

FILES = {
    'mil_soc_pavlik.ltx': PAVLIK,
    'mil_soc_ara.ltx': ARA,
    'mil_soc_ara_guard_1.ltx': guard(1, 'mil_smart_terrain_1_walker_5_walk', 'story|mil_soc_pavlik'),
    'mil_soc_ara_guard_2.ltx': guard(2, 'mil_smart_terrain_1_walker_4_walk', 'story|mil_soc_pavlik'),
    'mil_soc_ara_guard_3.ltx': guard(3, 'mil_smart_terrain_1_walker_5_walk', 'story|mil_soc_pavlik'),
    'mil_soc_cook.ltx': COOK,
}

for name, txt in FILES.items():
    assert all(ord(c) < 128 for c in txt), name
    with open(os.path.join(out, name), 'wb') as f:
        f.write(txt.encode('ascii'))
    print('wrote', name)
