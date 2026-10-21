"""Dialogs of Sakharov and Kruglov of the original SoC (idempotent). Edits files that other patches own (one patch per file); run it again
after patches\\quest_dialogs\\gen_quest_dialogs.py (which calls this script at its end):

  1. patches\\quest_dialogs\\...\\dialogs_coop_l08_yantar.xml
       - the level maker's dialogs  kruglov_x16_preparation / saharov_talk_to_the_saharov_x16 / _measurements / give_psi_protection_helmet /
         installation_is_disabled  are removed
       - new dialogs yan_soc_saharov_dialog (SoC yantar_general_ucheniy_talk_start) and yan_soc_kruglov_dialog (SoC yantar_help_scientist);
         the state of the talk comes from shared story flags (coop_soc_yan.script)
  2. patches\\repeatable_quests\\...\\character_desc_coop_l08_yantar.xml   Sakharov and Kruglov start with the SoC dialog and no longer list
     the removed ones (the fetch orders rq_sak_*, the generic topics and the greeting stay)
  3. patches\\repeatable_quests\\...\\coop_hidden_tasks.ltx   the tasks that are no longer given
  4. patches\\yantar_restore\\...\\spawn_sections_coop_l08_yantar.ltx   Vasiliev (corpse) and his PDA
  5. patches\\soc_yan_x16_quests\\gamedata\\scripts\\coop_soc_yan.script   the say_* functions between the BEGIN / END markers
"""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.dirname(here)
repo = os.path.dirname(os.path.dirname(patch))
P = lambda *a: os.path.join(repo, 'patches', *a)
NL = b'\r\n'
changed = []


def rw(path, fn):
    data = open(path, 'rb').read()
    new = fn(data)
    if new != data:
        open(path, 'wb').write(new)
        changed.append(os.path.relpath(path, repo))


def drop_dialog(data, did):
    return re.sub(rb'[ \t]*<dialog id="' + did.encode() + rb'">.*?</dialog>[ \t]*\r?\n', b'', data, flags=re.S)


# ---------------------------------------------------------------------------------------------------
# flags (see coop_soc_yan.script)
# ---------------------------------------------------------------------------------------------------
OFFERED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO'
PREP = 'YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO'
REPORTED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO'
HELMET = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO'
DONE = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO'
OUTFIT = 'YAN_SOC_OUTFIT_GIVEN'
REWARD = 'YAN_SOC_REWARD_GIVEN'

# phrases that close the window (SoC: dialogs.break_dialog); the other last phrases leave the topic list of the NPC open, like in SoC
S_END = ('2111211', '101412', '311114')
K_END = ('1111111',)


def ph(kind, pid, nxt=(), pre=(), flags=(), end=()):
    s = ['            <phrase id="%s">' % pid, '                <action>coop_soc_yan.say_%s%s</action>' % (kind, pid),
         '                <text>coop_soc_yan_%s_%s</text>' % (kind, pid)]
    s += ['                <precondition>coop_soc_yan.%s</precondition>' % p for p in pre]
    s += ['                <give_flag>%s</give_flag>' % f for f in flags]
    if pid in end:
        s.append('                <action>dialogs.break_dialog</action>')
    s += ['                <next>%s</next>' % n for n in nxt]
    s.append('            </phrase>')
    return s


def redirect(pid, pre, nxt):
    return ['            <phrase id="%s">' % pid, '                <text />', '                <precondition>coop_soc_yan.%s</precondition>' % pre,
            '                <next>%s</next>' % nxt, '            </phrase>']


S = ['    <dialog id="yan_soc_saharov_dialog">', '        <phrase_list>',
     '            <!-- original SoC yantar_general_ucheniy_talk_start (phrase ids are the SoC ids); the greeting is chosen by the state of the job -->',
     '            <phrase id="0">', '                <text />']
S += ['                <next>%s</next>' % n for n in ('1', '10', '3', '7', '6', '23', '99')]
S += ['            </phrase>']
# SoC branch 1: the offer (Kruglov not rescued at Rostok)
S += redirect('1', 'st_s_offer', '11')
S += ph('s', '11', ['111'])
S += ph('s', '111', ['211'])
S += ph('s', '211', ['2111'])
S += ph('s', '2111', ['21111'])
S += ph('s', '21111', ['21112', '21115'])
S += ph('s', '21112', ['211121'], flags=[OFFERED])
S += ph('s', '211121', ['2111211'])
S += ph('s', '2111211', end=S_END)
S += ph('s', '21115', ['211151'])
S += ph('s', '211151')
# SoC branch 10: Kruglov was rescued: the suit, then the same offer
S += redirect('10', 'st_s_offer_r', '101')
S += ph('s', '101', ['1011'], flags=[OUTFIT])
S += ph('s', '1011', ['1012'])
S += ph('s', '1012', ['1013'])
S += ph('s', '1013', ['1014'])
S += ph('s', '1014', ['10141', '10143'])
S += ph('s', '10141', ['101411'], flags=[OFFERED])
S += ph('s', '101411', ['101412'])
S += ph('s', '101412', end=S_END)
S += ph('s', '10143', ['101431'])
S += ph('s', '101431')
# SoC branch 3: the measurements are done: the artifact, the prototype helmet and the lab job (flags together in the first phrase so that a
# cut-off talk cannot lose them; the helmet and the artifact are handed out by the server tick)
S += redirect('3', 'st_s_results', '31')
S += ph('s', '31', ['311'], flags=[REPORTED, HELMET, REWARD])
S += ph('s', '311', ['3111'])
S += ph('s', '3111', ['31111'])
S += ph('s', '31111', ['311111'])
S += ph('s', '311111', ['311112'])
S += ph('s', '311112', ['311113'])
S += ph('s', '311113', ['311114'])
S += ph('s', '311114', end=S_END)
# SoC branch 7 / 6: reminders
S += redirect('7', 'st_s_wait', '71')
S += ph('s', '71')
S += redirect('6', 'st_s_lab', '61')
S += ph('s', '61')
# SoC branch 23: out of the lab
S += redirect('23', 'st_s_exit', '231')
S += ph('s', '231', ['2311'], flags=[DONE])
S += ph('s', '2311')
# nothing to do: the mod's usual greeting
S += redirect('99', 'st_s_done', '991')
S += ['            <phrase id="991">', '                <action>coop_pda_phrases.say__yan_smart_terrain_1_ecolog_saharov_start_dialog_0</action>',
      '                <text>yan_smart_terrain_1_ecolog_saharov_start_dialog_0</text>', '            </phrase>']
S += ['        </phrase_list>', '    </dialog>']

K = ['    <dialog id="yan_soc_kruglov_dialog">', '        <phrase_list>',
     '            <!-- original SoC yantar_help_scientist: Kruglov sends the player ahead to the measurement sites -->',
     '            <phrase id="0">', '                <text />']
K += ['                <next>%s</next>' % n for n in ('2', '4', '1', '10', '7')]
K += ['            </phrase>']
K += redirect('2', 'st_k_meet_r', '21')
K += ph('k', '21')
K += redirect('4', 'st_k_meet', '41')
K += ph('k', '41')
K += redirect('1', 'st_k_talk', '11')
K += ph('k', '11', ['111'])
K += ph('k', '111', ['1111'])
K += ph('k', '1111', ['11111'])
K += ph('k', '11111', ['111111'], flags=[PREP])
K += ph('k', '111111', ['1111111'])
K += ph('k', '1111111', end=K_END)
K += redirect('10', 'st_k_busy', '101')
K += ph('k', '101')
K += redirect('7', 'st_k_after', '71')
K += ph('k', '71')
K += ['        </phrase_list>', '    </dialog>']

NEWDLG = NL.join(x.encode('ascii') for x in S + K) + NL

OLD_DIALOGS = ('yan_smart_terrain_1_ecolog_kruglov_x16_preparation_dialog', 'yan_smart_terrain_1_ecolog_saharov_talk_to_the_saharov_x16_dialog',
               'yan_smart_terrain_1_ecolog_saharov_talk_to_the_saharov_measurements_dialog',
               'yan_smart_terrain_1_ecolog_saharov_give_psi_protection_helmet_dialog',
               'yan_smart_terrain_1_ecolog_saharov_installation_is_disabled_dialog')


def dialogs(data):
    for d in OLD_DIALOGS + ('yan_soc_saharov_dialog', 'yan_soc_kruglov_dialog'):
        data = drop_dialog(data, d)
    i = data.rindex(b'</game_dialogs>')
    return data[:i] + NEWDLG + data[i:]


rw(P('quest_dialogs', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l08_yantar.xml'), dialogs)


# ---------------------------------------------------------------------------------------------------
# characters
# ---------------------------------------------------------------------------------------------------
def chars(data):
    for cid, old, new, drop in (
            ('yan_smart_terrain_1_ecolog_saharov', 'yan_smart_terrain_1_ecolog_saharov_start_dialog', 'yan_soc_saharov_dialog',
             ('yan_smart_terrain_1_ecolog_saharov_talk_to_the_saharov_x16_dialog', 'yan_smart_terrain_1_ecolog_saharov_talk_to_the_saharov_measurements_dialog',
              'yan_smart_terrain_1_ecolog_saharov_give_psi_protection_helmet_dialog', 'yan_smart_terrain_1_ecolog_saharov_installation_is_disabled_dialog')),
            ('yan_smart_terrain_1_ecolog_kruglov', 'yan_smart_terrain_1_ecolog_kruglov_start_dialog', 'yan_soc_kruglov_dialog',
             ('yan_smart_terrain_1_ecolog_kruglov_x16_preparation_dialog',))):
        m = re.search(rb'<specific_character id="' + cid.encode() + rb'".*?</specific_character>', data, re.S)
        blk = m.group(0)
        nb = blk.replace(b'<start_dialog>' + old.encode() + b'</start_dialog>', b'<start_dialog>' + new.encode() + b'</start_dialog>')
        for d in drop:
            nb = re.sub(rb'[ \t]*<actor_dialog>' + d.encode() + rb'</actor_dialog>[ \t]*\r?\n', b'', nb)
        data = data[:m.start()] + nb + data[m.end():]
    return data


rw(P('repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l08_yantar.xml'), chars)

# ---------------------------------------------------------------------------------------------------
# tasks that are never given any more
# ---------------------------------------------------------------------------------------------------
HIDDEN = ['yan_start_go_to_yantar_quest_task', 'yan_start_take_measurements_1_quest_task', 'yan_start_take_measurements_2_quest_task',
          'yan_start_take_measurements_3_quest_task', 'yan_start_talk_to_the_saharov_quest_task', 'yan_start_configuring_helmets_quest_task',
          'yan_start_talk_to_the_saharov_x16_lab_quest_task', 'x16_start_turn_off_the_switch_1_task', 'x16_start_turn_off_the_switch_2_task',
          'x16_start_turn_off_the_switch_3_task', 'x16_start_turn_off_the_switch_4_task']
MARK = b'; Yantar and the X16 lab (patch soc_yan_x16_quests)'


def hidden(data):
    if MARK in data:
        return data
    text = NL.join([
        b'',
        MARK + b': the SoC tasks are one task each (yan_find_scientist, yan_find_vasilyev_task, yan_kill_brain_task, yan_kill_brain_task_2);',
        b'; the level maker\'s per-step tasks have no SoC objective of their own, "configuring helmets" is not in SoC (the helmet comes from Sakharov\'s dialog),',
        b'; bar_x16_documents is the single Barkeep task of patch bar_soc_quests. Their sections stay in the tm_coop files (old saves).'] +
        [h.encode() for h in HIDDEN]) + NL
    return data.rstrip(b'\r\n') + NL + text


rw(P('repeatable_quests', 'gamedata', 'configs', 'misc', 'coop_hidden_tasks.ltx'), hidden)

# ---------------------------------------------------------------------------------------------------
# Vasiliev and his PDA (spawn sections)
# ---------------------------------------------------------------------------------------------------
SPAWN = ('\r\n'
         ';--- soc_yan_x16_quests: Vasiliev (SoC yan_ecolog_vasilyev, dead ecologist in the swamp) and his PDA (SoC article yan_vasilyev_info) -----\r\n'
         '; created by coop_soc_yan.script when the lab job starts; the corpse has the story id the task marker needs\r\n'
         '[yan_vasilyev]:stalker\r\n'
         'character_profile\t\t\t= sim_default_ecolog_1\r\n'
         'spec_rank\t\t\t\t\t= veteran\r\n'
         'community\t\t\t\t\t= ecolog\r\n'
         'story_id\t\t\t\t\t= yan_vasilyev\r\n'
         '\r\n'
         '[yan_vasilyev_pda]:quest_item_base\r\n'
         '$spawn \t\t\t\t= "quest_items\\yan_vasilyev_pda"\r\n'
         'visual\t\t\t\t= dynamics\\devices\\dev_pda\\dev_pda.ogf\r\n'
         'description\t\t\t= coop_soc_yan_vasilyev_pda_descr\r\n'
         'inv_name\t\t\t= coop_soc_yan_vasilyev_pda_name\r\n'
         'inv_name_short\t\t= coop_soc_yan_vasilyev_pda_name\r\n'
         'cost \t\t\t\t= 0\r\n'
         'inv_grid_x\t\t\t= 6\r\n'
         'inv_grid_y\t\t\t= 13\r\n').encode('ascii')


def spawn(data):
    if b'[yan_vasilyev]' in data:
        return data
    return data.rstrip(b'\r\n') + b'\r\n' + SPAWN


rw(P('yantar_restore', 'gamedata', 'configs', 'creatures', 'spawn_sections_coop_l08_yantar.ltx'), spawn)

# ---------------------------------------------------------------------------------------------------
# the say_* functions of coop_soc_yan.script
# ---------------------------------------------------------------------------------------------------
sys.path.insert(0, here)
S_IDS = re.findall(r'<phrase id="([0-9]+)">\s*<action>coop_soc_yan\.say_s', NEWDLG.decode())
K_IDS = re.findall(r'<phrase id="([0-9]+)">\s*<action>coop_soc_yan\.say_k', NEWDLG.decode())
block = ['-- BEGIN say (written by tools\\apply_dialogs.py, do not edit by hand)']
block += ['function say_s%s(a, b) say("s", "%s", a, b) end' % (i, i) for i in S_IDS]
block += ['function say_k%s(a, b) say("k", "%s", a, b) end' % (i, i) for i in K_IDS]
block += ['-- END say']
BLOCK = '\n'.join(block).encode('ascii')


def script(data):
    return re.sub(rb'-- BEGIN say.*?-- END say', lambda m: BLOCK, data, flags=re.S)


rw(os.path.join(patch, 'gamedata', 'scripts', 'coop_soc_yan.script'), script)

print('changed:', changed if changed else 'nothing (already applied)')
