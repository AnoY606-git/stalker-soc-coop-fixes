"""Characters, profiles, spawn sections, logic files and the quest items of patch soc_bar_duty_line (idempotent, generated).
  python gen_chars.py <mod source gamedata.db0 dir>
Writes under patches\\soc_bar_duty_line\\gamedata:
  configs\\gameplay\\character_desc_coop_soc_duty.xml   specific characters of the new NPCs (SoC ids; visuals reused from the mod)
  configs\\gameplay\\npc_profile_coop_soc_duty.xml       their profiles
  configs\\creatures\\spawn_sections_coop_l06_rostok.ltx the mod's file + the spawn sections of the new NPCs and the two PDA items
  configs\\scripts\\coop_l05_bar\\soc_duty_stand.ltx, coop_l06_rostok\\soc_vet_stand.ltx   logic (remark scheme, no path needed)
Visuals, voices and weapons are ones the mod already uses, so the patch adds no model, texture or sound."""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import duty_model as M

GD = os.path.join(os.path.dirname(here), 'gamedata')
NL = '\r\n'
if len(sys.argv) < 2:
    sys.exit('usage: gen_chars.py <mod source gamedata.db0 dir>')
MOD = sys.argv[1]

DUTY_SUP = ['wpn_abakan_m2', 'ammo_5.45x39_ap = 1', 'wpn_hpsa', 'ammo_9x19_fmj = 1', 'grenade_rgd5 = 1']
BAND_SUP = ['wpn_abakan_m2', 'ammo_5.45x39_ap = 1', 'wpn_hpsa', 'ammo_9x19_fmj = 1', 'grenade_rgd5 = 1']
KILL_SUP = ['wpn_l85_m1', 'ammo_5.56x45_ap = 1', 'wpn_usp', 'ammo_11.43x23_hydro = 1', 'grenade_rgo = 1']

# id, name string, bio string, community, rank, reputation, visual, snd_config, supplies, money, spec_rank, logic file (custom_data), dialogs
CHARS = [
    dict(id='bar_dolg_guard_commander', section='soc_duty_guard_commander', name='coop_soc_duty_commander_name', bio='coop_soc_duty_commander_bio',
         comm='dolg', rank=1200, rep=300, visual=r'actors\stalker_dolg\stalker_dolg_3', snd=r'characters_voice\human_02\dolg' + '\\', sup=DUTY_SUP,
         money=(200, 600), spec='regular', logic=r'scripts\coop_l05_bar\soc_duty_stand.ltx', story=M.NPC['commander'], dlg=M.NEW_DIALOG_CHARS['bar_dolg_guard_commander']),
    dict(id='bar_dolg_ivancov', section='soc_duty_ivancov', name='coop_soc_duty_ivancov_name', bio='coop_soc_duty_ivancov_bio',
         comm='dolg', rank=2071, rep=500, visual=r'actors\stalker_dolg\stalker_dolg_4', snd=r'characters_voice\human_02\dolg' + '\\', sup=DUTY_SUP,
         money=(200, 600), spec='veteran', logic=r'scripts\coop_l05_bar\soc_duty_stand.ltx', story=M.NPC['ivancov'], dlg=M.NEW_DIALOG_CHARS['bar_dolg_ivancov']),
    dict(id='bar_crazy_veterans_lucky', section='soc_vet_lucky', name='coop_soc_duty_lucky_name', bio='coop_soc_duty_lucky_bio',
         comm='bandit', rank=2071, rep=-400, visual=r'actors\stalker_bandit\stalker_bandit_4', snd=r'characters_voice\human_01\bandit' + '\\', sup=BAND_SUP,
         money=(600, 2000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=M.NPC['lucky'], dlg=None),
    dict(id='bar_crazy_veterans_1', section='soc_vet_1', name='GENERATE_NAME_bandit', bio='none',
         comm='bandit', rank=1200, rep=-400, visual=r'actors\stalker_bandit\stalker_bandit_1', snd=r'characters_voice\human_01\bandit' + '\\', sup=BAND_SUP,
         money=(300, 1000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=None, dlg=None),
    dict(id='bar_crazy_veterans_2', section='soc_vet_2', name='GENERATE_NAME_bandit', bio='none',
         comm='bandit', rank=1200, rep=-400, visual=r'actors\stalker_bandit\stalker_bandit_2', snd=r'characters_voice\human_01\bandit' + '\\', sup=BAND_SUP,
         money=(300, 1000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=None, dlg=None),
    dict(id='bar_killer_ambush_tiran', section='soc_tyran', name='coop_soc_duty_tyran_name', bio='coop_soc_duty_tyran_bio',
         comm='killer', rank=2071, rep=-600, visual=r'actors\stalker_merc\stalker_merc_2', snd=r'characters_voice\human_03\killer' + '\\', sup=KILL_SUP,
         money=(2000, 5000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=M.NPC['tyran'], dlg=None),
    dict(id='soc_duty_merc_1', section='soc_merc_1', name='GENERATE_NAME_stalker', bio='none',
         comm='killer', rank=1200, rep=-600, visual=r'actors\stalker_merc\stalker_merc_2', snd=r'characters_voice\human_03\killer' + '\\', sup=KILL_SUP,
         money=(1000, 3000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=None, dlg=None),
    dict(id='soc_duty_merc_2', section='soc_merc_2', name='GENERATE_NAME_stalker', bio='none',
         comm='killer', rank=1200, rep=-600, visual=r'actors\stalker_merc\stalker_merc_2', snd=r'characters_voice\human_03\killer' + '\\', sup=KILL_SUP,
         money=(1000, 3000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=None, dlg=None),
    dict(id='soc_duty_merc_3', section='soc_merc_3', name='GENERATE_NAME_stalker', bio='none',
         comm='killer', rank=1200, rep=-600, visual=r'actors\stalker_merc\stalker_merc_2', snd=r'characters_voice\human_03\killer' + '\\', sup=KILL_SUP,
         money=(1000, 3000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=None, dlg=None),
    dict(id='soc_duty_merc_4', section='soc_merc_4', name='GENERATE_NAME_stalker', bio='none',
         comm='killer', rank=1200, rep=-600, visual=r'actors\stalker_merc\stalker_merc_2', snd=r'characters_voice\human_03\killer' + '\\', sup=KILL_SUP,
         money=(1000, 3000), spec='veteran', logic=r'scripts\coop_l06_rostok\soc_vet_stand.ltx', story=None, dlg=None),
]


def write(path, text, enc='ascii'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = text.replace('\r\n', '\n').replace('\n', NL).encode(enc)
    old = open(path, 'rb').read() if os.path.exists(path) else None
    if old != data:
        open(path, 'wb').write(data)
        print('written', os.path.relpath(path, GD))
    else:
        print('unchanged', os.path.relpath(path, GD))


def char_xml(c):
    L = ['<specific_character id="%s" team_default = "1">' % c['id'],
         '    <name>%s</name>' % c['name'],
         '    <icon>ui_inGame2_neutral_0_3</icon>',
         '    <map_icon x="0" y="0"></map_icon>',
         '    <bio>%s</bio>' % c['bio'],
         '    <class>%s</class>' % c['id'],
         '    <community>%s</community> <terrain_sect>stalker_terrain</terrain_sect>' % c['comm'],
         '    <money min="%d" max="%d" infinitive="0"></money>' % c['money'],
         '    <rank>%d</rank>' % c['rank'],
         '    <reputation>%d</reputation>' % c['rep'],
         '    <visual>%s</visual>' % c['visual'],
         '    <snd_config>%s</snd_config>' % c['snd'],
         '    <crouch_type>-1</crouch_type>',
         '    <supplies>',
         '      [spawn] \\n']
    L += ['      %s \\n' % s for s in c['sup']]
    L += ['    </supplies>', '#include "gameplay\\character_criticals_4.xml"']
    if c['dlg'] is not None:
        start, acts = c['dlg']
        L.append('    <start_dialog>%s</start_dialog>' % start)
        for a in acts:
            L.append('    <actor_dialog>%s</actor_dialog>' % a)
        L.append('    <actor_dialog>actor_break_dialog</actor_dialog>')
    L.append('</specific_character>')
    return L


# ---- character_desc_coop_soc_duty.xml
L = ["<?xml version='1.0' encoding=\"windows-1251\"?>", '<xml>',
     '    <!-- GENERATED by patches\\soc_bar_duty_line\\tools\\gen_chars.py: SoC ids of the Duty line NPCs, visuals / voices / weapons the mod already uses -->']
for c in CHARS:
    L += char_xml(c)
L.append('</xml>')
write(os.path.join(GD, 'configs', 'gameplay', 'character_desc_coop_soc_duty.xml'), '\n'.join(L) + '\n', 'cp1251')

# ---- npc_profile_coop_soc_duty.xml
L = ["<?xml version='1.0' encoding=\"UTF-8\"?>", '<xml>']
for c in CHARS:
    L += ['\t<character id="%s">' % c['id'], '\t\t<class>%s</class>' % c['id'], '\t</character>']
L.append('</xml>')
write(os.path.join(GD, 'configs', 'gameplay', 'npc_profile_coop_soc_duty.xml'), '\n'.join(L) + '\n')

# ---- spawn sections: the mod's l06 file + our block
BEGIN, END = '; ---- soc_bar_duty_line begin (generated by tools\\gen_chars.py) ----', '; ---- soc_bar_duty_line end ----'
src = os.path.join(MOD, 'configs', 'creatures', 'spawn_sections_coop_l06_rostok.ltx')
base = open(src, 'rb').read().decode('ascii').replace('\r\n', '\n')
if BEGIN in base:
    base = base[:base.index(BEGIN)].rstrip('\n') + '\n'
B = [BEGIN]
for c in CHARS:
    B += ['', '[%s]:stalker' % c['section'], '$spawn\t\t\t\t\t\t= "respawn\\%s"' % c['section'], 'character_profile\t\t\t= %s' % c['id'],
          'spec_rank\t\t\t\t\t= %s' % c['spec'], 'community\t\t\t\t\t= %s' % c['comm']]
    if c['story']:
        B.append('story_id\t\t\t\t\t= %s' % c['story'])
    B.append('custom_data\t\t\t\t\t= %s' % c['logic'])
for k, name, desc in (('lucky', 'coop_soc_duty_lucky_pda_name', 'coop_soc_duty_lucky_pda_desc'), ('tyran', 'coop_soc_duty_tyran_pda_name', 'coop_soc_duty_tyran_pda_desc')):
    p = M.PDAS[k]
    B += ['', '; the PDA of %s (SoC quest_items.ltx bar_%s_pda); made by the script when he is dead, see coop_soc_duty.script' % (k, 'lucky' if k == 'lucky' else 'tiran'),
          '[%s]:quest_item_base' % p['section'], '$spawn\t\t\t\t\t\t= quest_items\\%s' % p['section'],
          'visual\t\t\t\t\t\t= dynamics\\devices\\dev_pda\\dev_pda.ogf', 'description\t\t\t\t\t= %s' % desc, 'inv_name\t\t\t\t\t= %s' % name,
          'inv_name_short\t\t\t\t= %s' % name, 'cost\t\t\t\t\t\t= 0', 'inv_grid_x\t\t\t\t\t= 6', 'inv_grid_y\t\t\t\t\t= 13']
B.append(END)
write(os.path.join(GD, 'configs', 'creatures', 'spawn_sections_coop_l06_rostok.ltx'), base.rstrip('\n') + '\n\n' + '\n'.join(B) + '\n')

# ---- logic files
STAND = """; Bar Duty line (patch soc_bar_duty_line): the gate commander and Captain Ivantsov stand where they stood in the original SoC.
; Started by their spawn section (custom_data) or, if the engine did not read it, by coop_soc_duty.script ensure_logic().
[logic]
active = remark@soc_duty_stand

[remark@soc_duty_stand]
anim = guard
target = nil
meet = meet@soc_duty_stand
invulnerable = true
combat_ignore_cond = true
combat_ignore_keep_when_attacked = true
gather_items_enabled = false
help_wounded_enabled = false
corpse_detection_enabled = false
use_camp = false

[meet@soc_duty_stand]
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
"""
HOSTILE = """; Mad veterans' camp and the Mercs of the construction site (patch soc_bar_duty_line): they stand guard where SoC had them and fight any player
; (the script sets the relation to enemy for every player). Started by the spawn section (custom_data) or by coop_soc_duty.script ensure_logic().
[logic]
active = remark@soc_vet_stand

[remark@soc_vet_stand]
anim = guard
target = nil
meet = meet@soc_vet_stand
gather_items_enabled = false
help_wounded_enabled = false
corpse_detection_enabled = false
use_camp = false

[meet@soc_vet_stand]
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
use = false
allow_break = true
meet_on_talking = false
"""
write(os.path.join(GD, 'configs', 'scripts', 'coop_l05_bar', 'soc_duty_stand.ltx'), STAND)
write(os.path.join(GD, 'configs', 'scripts', 'coop_l06_rostok', 'soc_vet_stand.ltx'), HOSTILE)
