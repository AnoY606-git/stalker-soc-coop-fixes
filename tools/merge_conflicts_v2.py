# One-off merge of files that two patches shipped (2026-10-19, before the v2 release build).
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'patches')

def rd(*a): return open(os.path.join(P, *a), 'rb').read()
def wr(data, *a): open(os.path.join(P, *a), 'wb').write(data)
def rm(*a): os.remove(os.path.join(P, *a))

# 1. stalkers_upgrade_info.ltx: weapon_upgrades copy + the Cordon technician block from cordon_technician
f = ('gamedata', 'configs', 'misc', 'stalkers_upgrade_info.ltx')
tech = rd('cordon_technician', *f)
i = tech.find(b';**** Cordon rookie technician')
i = tech.rfind(b';****', 0, i)  # start of the banner line above it
block = tech[i:]
upg = rd('weapon_upgrades', *f)
if b'[esc_rookie_technician]' not in upg:
    upg = upg.rstrip(b'\r\n') + b'\r\n\r\n' + block
    wr(upg, 'weapon_upgrades', *f)
rm('cordon_technician', *f)
print('1 merged technician block into weapon_upgrades')

# 2. x18 get-out restrictor: darkvalley_restore copy with the any-player trigger
f = ('gamedata', 'configs', 'scripts', 'coop_l04_darkvalley', 'space_restrictors', 'x18_start_get_out_of_the_lab_quest_task_space_restrictor.ltx')
d = rd('darkvalley_restore', *f)
assert d.count(b'on_actor_inside') == 1
wr(d.replace(b'on_actor_inside', b'on_any_player_inside'), 'darkvalley_restore', *f)
rm('any_player_restrictors', *f)
print('2 x18 restrictor merged into darkvalley_restore')

# 3. Cordon start-quest restrictor: cutscenes_pkg_opening copy already contains the cordon changes
f = ('gamedata', 'configs', 'scripts', 'coop_l01_escape', 'space_restrictors', 'esc_start_main_quest_task_space_restrictor.ltx')
rm('cordon', *f)
print('3 removed cordon copy (cutscenes_pkg_opening is a superset)')

# 4. Escape dialogs: kept in both. quest_dialogs' copy is generated from cordon's (gen_quest_dialogs.py reads it) and wins
#    in build order (sorted: cordon < quest_dialogs), so nothing to do.
