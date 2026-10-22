"""Writes the config files of patch soc_aes_war (idempotent):

  python gen_configs.py <mod source gamedata.db0\\configs>      (the mod's own spawn_sections_coop_l11_control_monolith.ltx is the base)

  gamedata\\configs\\scripts\\coop_l11_stancia_1\\aes_1_heli_attack_<1..8>.ltx   new logic of the 8 helicopters of the mod
  gamedata\\configs\\scripts\\coop_l11_stancia_1\\soc_aes_btr.ltx                logic of the BTR (ph_car, army route)
  gamedata\\configs\\creatures\\spawn_sections_coop_l11_control_monolith.ltx     the mod's file byte for byte + section [soc_aes_btr]
  gamedata\\configs\\misc\\coop_aes_war.ltx                                      switches

The 8 helicopters sit in all.spawn with `cfg = scripts\\coop_l11_stancia_1\\aes_1_heli_attack_<n>.ltx`, so replacing those files changes their logic without touching all.spawn.
Old saves keep working: the old section names (heli_move@idle / fly_ready / fly_0 / fly_1) stay, a save stores the active section by name.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.dirname(HERE)
GD = os.path.join(PATCH, 'gamedata', 'configs')
if len(sys.argv) < 2:
    sys.exit(__doc__)
mod_cfg = sys.argv[1]

# route of each helicopter after take-off: its own loop of the mod (aes_1_helicopter_<n>_move_way_0); heli 1 had a one point route and a second
# route that does not exist (aes_1_helicopter_1_move_way_1 = engine abort), it now flies the loop of heli 7, taking off 8 s after heli 7
LOOP = {1: 7, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8}
# take-off delay in ms after the go signal (one after the other, like the SoC waves)
DELAY = {1: 38000, 2: 5000, 3: 10000, 4: 15000, 5: 20000, 6: 25000, 7: 30000, 8: 35000}

HELI = """; CNPP-1 helicopter {n} (patch soc_aes_war, v1.4.3). Old v1.4.2 file: it flew its route and never fired; now it patrols the loop and the script
; coop_soc_aes_war gives it enemies (Monolith soldiers, players inside the SoC helicopter zones). Machine gun only.
; The section names of the old file are kept (a save stores the active section by name).
[logic]
active = heli_move@idle

; waits in the yard behind the start until the party is here ({{+SOC_AESW_GO}} is given by the script) or the mod's own quest flag is set
[heli_move@idle]
path_move = aes_1_helicopter_{n}_idle_way
max_velocity = 300
engine_sound = false
use_rocket = false
on_info = {{+PRI_START_GO_TO_CNPP_QUEST_TASK_INFO}} heli_move@fly_ready, {{+SOC_AESW_GO}} heli_move@fly_ready

[heli_move@fly_ready]
path_move = aes_1_helicopter_{n}_idle_way
max_velocity = 150
engine_sound = true
use_rocket = false
on_timer = {delay} | heli_move@fly_0

[heli_move@fly_0]
path_move = aes_1_helicopter_{loop}_move_way_0
max_velocity = 150
engine_sound = true
use_rocket = false
on_timer = 7000 | heli_move@fly_1

[heli_move@fly_1]
path_move = aes_1_helicopter_{loop}_move_way_0
max_velocity = 90
engine_sound = true
use_rocket = false
use_mgun = true
"""

BTR_LOGIC = """; The army BTR of CNPP-1 (patch soc_aes_war): the SoC aes_btr_0002 that drives up the road to the Sarcophagus entrance.
; Created by the server script coop_soc_aes_war (section soc_aes_btr, custom_data = this file). It follows the last part of the mod's army assault route
; (smart terrain 5, point 9 = its start, the end 62 m before the entrance) and stops there. Its gun is run by the script (Monolith soldiers only).
[logic]
active = ph_car@drive

[ph_car@drive]
path_walk = aes_1_smart_terrain_5_walker_army_ordinary_7_walk
headlights = off
"""

SECTION = """
; The army BTR of CNPP-1 (patch soc_aes_war): the script car of Call of Pripyat (class SCRPTCAR like m_car, script_binding bind_car.init) with the BTR
; model and its machine gun (configs\\models\\vehicles\\veh_btr_script_u_01.ltx). Created once by scripts\\coop_soc_aes_war.script.
; (m_car is defined later in system.ltx than this include, so its keys are repeated here instead of inheriting them.)
[soc_aes_btr]
GroupControlSection      = spawn_group
discovery_dependency     =
$spawn                   = "vehicles\\car"
cform                    = skeleton
class                    = SCRPTCAR
inv_weight               = 1000
cost                     = 100000
inv_grid_width           = 1
inv_grid_height          = 1
script_binding           = bind_car.init
visual                   = dynamics\\vehicles\\btr\\veh_btr_script_u_01.ogf
story_id                 = soc_aes_btr
custom_data              = scripts\\coop_l11_stancia_1\\soc_aes_btr.ltx
"""

SWITCH = """; patch soc_aes_war (CNPP-1, coop_l11_stancia_1). true / false.
; helicopters = the 8 helicopters shoot at Monolith soldiers (and at players in the SoC helicopter zones)
; btr         = the army BTR is created on the road to the Sarcophagus
[soc_aes_war]
helicopters = true
btr         = true
"""


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('ascii'))


for n in range(1, 9):
    w(os.path.join(GD, 'scripts', 'coop_l11_stancia_1', 'aes_1_heli_attack_%d.ltx' % n),
      HELI.format(n=n, loop=LOOP[n], delay=DELAY[n]))
w(os.path.join(GD, 'scripts', 'coop_l11_stancia_1', 'soc_aes_btr.ltx'), BTR_LOGIC)
base = open(os.path.join(mod_cfg, 'creatures', 'spawn_sections_coop_l11_control_monolith.ltx'), 'rb').read().decode('ascii').replace('\r\n', '\n')
w(os.path.join(GD, 'creatures', 'spawn_sections_coop_l11_control_monolith.ltx'), base.rstrip('\n') + '\n' + SECTION)
w(os.path.join(GD, 'misc', 'coop_aes_war.ltx'), SWITCH)
print('written')
