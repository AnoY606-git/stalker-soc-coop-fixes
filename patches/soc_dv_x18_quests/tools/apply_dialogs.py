"""Barkeep dialog of the original SoC (idempotent). Edits files that other patches own (one patch per file), run again after
patches\\quest_dialogs\\gen_quest_dialogs.py (which calls this script at its end):

  1. patches\\quest_dialogs\\...\\dialogs_coop_l05_bar.xml
       - the three level-maker dialogs  has_documents_agroprom / go_to_darkvalley / 1_has_documents_darkvalley  are removed
       - new dialog bar_soc_barmen_start_dialog = SoC bar_bar_barmen_start (states by shared flags, see coop_soc_bar.script)
  2. patches\\repeatable_quests\\...\\character_desc_coop_l05_bar.xml   the Barkeep (bar_smart_terrain_1_stalker_barmen) starts with the SoC
       dialog and no longer lists the three removed dialogs (other NPCs keep the mod's greeting)
  3. patches\\repeatable_quests\\...\\character_desc_coop_l01_escape.xml and patches\\darkvalley_restore\\...\\dialogs_coop_l04_darkvalley.xml
       Sidorovich no longer takes the X18 documents (SoC: they go to the Barkeep): dialog and its list entry removed
"""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
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
# 1. the SoC Barkeep dialog
# ---------------------------------------------------------------------------------------------------
GO = 'BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO'
AGR = 'BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO'
AGR_OLD = 'BAR_SMART_TERRAIN_1_TRADER_BARMEN_AGR_DOC_INFO'
DONE = 'BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO'
X16_START = 'BAR_X16_DOCUMENTS_START'                                   # SoC bar_x16_documents_start (patch bar_soc_quests)
X16_DONE = 'BAR_X16_DOCUMENTS_DONE'                                     # SoC bar_x16_documents_done
RADAR = 'BAR_DEACTIVATE_RADAR_START'                                    # SoC bar_deactivate_radar_start
GO_MIL = 'BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_MILITARY_STOP_DIALOG_INFO'   # the mod's own flag, read by the Military / Radar / Stancia restrictors
END = ('2111', '15113', '15115', '172131', '172141', '1731', '121211', '1316', '1321')   # last phrase of a talk: the window closes


def ph(pid, nxt=(), pre=(), extra=(), text=True, say=True):
    s = ['            <phrase id="%s">' % pid]
    if say:
        s.append('                <action>coop_soc_bar.say_%s</action>' % pid)
    s.append('                <text>coop_soc_barman_%s</text>' % pid if text else '                <text />')
    s += ['                <precondition>coop_soc_bar.%s</precondition>' % p for p in pre]
    s += ['                ' + e for e in extra]
    if pid in END:
        s.append('                <action>dialogs.break_dialog</action>')
    s += ['                <next>%s</next>' % n for n in nxt]
    s.append('            </phrase>')
    return s


def redirect(pid, pre, nxt):
    return ['            <phrase id="%s">' % pid, '                <text />', '                <precondition>coop_soc_bar.%s</precondition>' % pre,
            '                <next>%s</next>' % nxt, '            </phrase>']


L = ['    <dialog id="bar_soc_barmen_start_dialog">', '        <phrase_list>',
     '            <!-- original SoC bar_bar_barmen_start (phrase ids are the SoC ids); the greeting is chosen by the state of the job -->',
     '            <phrase id="0">', '                <text />']
L += ['                <next>%s</next>' % n for n in ('1', '15', '12', '13', '16', '19', '18', '17', '3')]
L += ['            </phrase>']
# Agroprom documents (SoC 1 / 2 / 21 / 211 / 2111 / 22 / 221 / 2211)
L += redirect('1', 'st_agroprom', '2')
L += ph('2', ['21', '22'])
L += ph('21', ['211'])
L += ph('211', ['2111'])
L += ph('2111')
L += ph('22', ['221'], pre=['has_agroprom_docs'])
L += ph('221', ['2211'])
L += ph('2211', ['151'], extra=['<action>coop_soc_bar.take_agroprom_docs</action>', '<action>coop_soc_bar.reward_agroprom</action>',
                                '<give_flag>%s</give_flag>' % AGR, '<give_flag>%s</give_flag>' % AGR_OLD])
# the X18 job (SoC 15 / 151 / 1511 / 15111 / 15112 / 15113 / 15114 / 15115)
L += redirect('15', 'st_offer', '151')
L += ph('151', ['1511'])
L += ph('1511', ['15111'])
L += ph('15111', ['15112', '15114'])
L += ph('15112', ['15113'], extra=['<give_flag>%s</give_flag>' % GO])
L += ph('15113')
L += ph('15114', ['15115'])
L += ph('15115')
# job accepted, documents not found yet (SoC 18 / 181)
L += redirect('18', 'st_wait', '181')
L += ph('181')
# X18 documents (SoC 17 / 171 / 172 / 173 / 1731) and the X16 job speech (1721 / 17211 / 17212 / 17213 / 17214 / 172131 / 172141)
L += redirect('17', 'st_docs', '171')
L += ph('171', ['172', '173'])
L += ph('172', ['1721'], pre=['has_x18_docs'],
        extra=['<action>coop_soc_bar.take_x18_docs</action>', '<action>coop_soc_bar.reward_x18</action>', '<give_flag>%s</give_flag>' % DONE])
L += ph('173', ['1731'])
L += ph('1731')
L += ph('1721', ['17211'])
L += ph('17211', ['17212'])
L += ph('17212', ['17213', '17214'])
L += ph('17213', ['172131'], extra=['<give_flag>%s</give_flag>' % X16_START])
L += ph('172131')
L += ph('17214', ['172141'])
L += ph('172141')
# X18 hand-in done, X16 job not accepted yet (SoC 19: the speech 1721 again)
L += redirect('19', 'st_x16offer', '1721')
# X16 documents (SoC 12 / 121 / 1211 / 1212 / 12121 / 121211); the documents are taken and the flag set in the SAME phrase
L += redirect('12', 'st_x16docs', '121')
L += ph('121', ['1211', '1212'])
L += ph('1211', ['131'], pre=['has_x16_docs'],
        extra=['<action>coop_soc_bar.take_x16_docs</action>', '<give_flag>%s</give_flag>' % X16_DONE])
L += ph('1212', ['12121'])
L += ph('12121', ['121211'])
L += ph('121211')
# the Brain Scorcher job (SoC 13 / 131 / 1312 / 13121 / 1313 / 1314 / 1315 / 1316 / 132 / 1321). The accepted job also sets the mod's flag
# of the old go_to_military dialog, which the Military / Radar / Stancia restrictors still read
L += redirect('13', 'st_radaroffer', '131')
L += ph('131', ['1312', '132'])
L += ph('1312', ['13121'], extra=['<give_flag>%s</give_flag>' % RADAR, '<give_flag>%s</give_flag>' % GO_MIL])
L += ph('13121', ['1313'])
L += ph('1313', ['1314'])
L += ph('1314', ['1315'])
L += ph('1315', ['1316'])
L += ph('1316')
L += ph('132', ['1321'])
L += ph('1321')
# job accepted: the Barkeep just greets (SoC 16 / 161)
L += redirect('16', 'st_radar', '161')
L += ph('161')
# nothing to do yet / afterwards: the mod's usual greeting
L += redirect('3', 'st_default', '31')
L += ['            <phrase id="31">', '                <action>coop_pda_phrases.say__bar_smart_terrain_1_trader_barmen_start_dialog_0</action>',
      '                <text>bar_smart_terrain_1_trader_barmen_start_dialog_0</text>', '            </phrase>']
L += ['        </phrase_list>', '    </dialog>']
NEWDLG = NL.join(x.encode('ascii') for x in L) + NL

# three preconditions of phrase 172 (the co-op check of patch x18: any living player may hold a document)
NEWDLG = NEWDLG.replace(b'                <precondition>coop_soc_bar.has_x18_docs</precondition>' + NL,
                        NL.join(b'                <precondition>dialogs_coop_l05_bar.if_actor_has_dev_document_%d_x18</precondition>' % i for i in (1, 2, 3)) + NL)


def bar(data):
    for d in ('bar_smart_terrain_1_trader_barmen_has_documents_agroprom_dialog', 'bar_smart_terrain_1_stalker_barmen_go_to_darkvalley_dialog',
              'bar_smart_terrain_1_stalker_barmen_1_has_documents_darkvalley_dialog', 'bar_soc_barmen_start_dialog'):
        data = drop_dialog(data, d)
    i = data.rindex(b'</game_dialogs>')
    return data[:i] + NEWDLG + data[i:]


rw(P('quest_dialogs', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l05_bar.xml'), bar)


# ---------------------------------------------------------------------------------------------------
# 2. character: the Barkeep
# ---------------------------------------------------------------------------------------------------
def chars(data):
    m = re.search(rb'<specific_character id="bar_smart_terrain_1_stalker_barmen".*?</specific_character>', data, re.S)
    blk = m.group(0)
    nb = blk.replace(b'<start_dialog>bar_smart_terrain_1_trader_barmen_start_dialog</start_dialog>', b'<start_dialog>bar_soc_barmen_start_dialog</start_dialog>')
    for d in ('bar_smart_terrain_1_trader_barmen_has_documents_agroprom_dialog', 'bar_smart_terrain_1_stalker_barmen_go_to_darkvalley_dialog',
              'bar_smart_terrain_1_stalker_barmen_1_has_documents_darkvalley_dialog'):
        nb = re.sub(rb'[ \t]*<actor_dialog>' + d.encode() + rb'</actor_dialog>[ \t]*\r?\n', b'', nb)
    return data[:m.start()] + nb + data[m.end():]


rw(P('repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l05_bar.xml'), chars)


# ---------------------------------------------------------------------------------------------------
# 3. Sidorovich does not take the X18 documents
# ---------------------------------------------------------------------------------------------------
rw(P('repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l01_escape.xml'),
   lambda d: re.sub(rb'[ \t]*<actor_dialog>esc_smart_terrain_1_trader_sidorovich_x18_documents</actor_dialog>[ \t]*\r?\n', b'', d))
rw(P('darkvalley_restore', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l04_darkvalley.xml'),
   lambda d: drop_dialog(d, 'esc_smart_terrain_1_trader_sidorovich_x18_documents'))

print('changed:', changed if changed else 'nothing (already applied)')
