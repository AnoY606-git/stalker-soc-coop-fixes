# Puts stalkers_upgrade_info.ltx back into cordon_technician (mod original + the technician block), so the release can
# leave patches/weapon_upgrades out. weapon_upgrades keeps its own merged copy for when it is fixed.
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'patches')
rel = os.path.join('gamedata', 'configs', 'misc', 'stalkers_upgrade_info.ltx')
orig = open(os.path.expandvars(r'%USERPROFILE%\Downloads\Shadow of COOP 8.0\source\gamedata.db0\configs\misc\stalkers_upgrade_info.ltx'), 'rb').read()
upg = open(os.path.join(P, 'weapon_upgrades', rel), 'rb').read()
i = upg.find(b';**** Cordon rookie technician')
i = upg.rfind(b';****', 0, i)
block = upg[i:]
out = os.path.join(P, 'cordon_technician', rel)
open(out, 'wb').write(orig.rstrip(b'\r\n') + b'\r\n\r\n' + block)
print('wrote', out, len(block), 'bytes of technician block')
