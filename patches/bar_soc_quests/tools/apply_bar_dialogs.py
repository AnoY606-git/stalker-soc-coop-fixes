"""Bar dialogs, characters and hidden tasks of patch bar_soc_quests (idempotent). Edits files that other patches own (one patch per file); run it
again after patches\\quest_dialogs\\gen_quest_dialogs.py (that script calls it at its end, after soc_dv_x18_quests\\tools\\apply_dialogs.py which builds the
Barkeep dialog with the X16 documents and the Brain Scorcher job):

  1. patches\\quest_dialogs\\...\\dialogs_coop_l05_bar.xml
       - removed: the level maker's go_to_military dialog of the Barkeep (the Scorcher job is the SoC dialog now), the informant's "meeting place cannot be
         changed" dialog (mod-only story, already unlisted by the mod), the three hunter dialogs (start, quest, quest idle)
       - new: bar_soc_hunter_start_dialog / bar_soc_hunter_quest_dialog / bar_soc_hunter_finish_dialog (SoC bar_bar_hunter_*)
  2. patches\\repeatable_quests\\...\\character_desc_coop_l05_bar.xml   the Barkeep no longer lists go_to_military; the hunter starts with the SoC dialog
  3. patches\\repeatable_quests\\...\\coop_hidden_tasks.ltx             the mod-only tasks "meeting place cannot be changed" x3 and the duplicate
       ros_start_go_to_yantar (the one SoC task bar_x16_documents is bar_start_go_to_yantar_quest_task)
"""
import os
import re

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


ACCEPT = 'BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_STOP_DIALOG_INFO'
DONE = 'BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_IDLE_STOP_DIALOG_INFO'


def ph(pid, text, nxt=(), pre=(), extra=(), say=True, brk=False):
    s = ['            <phrase id="%s">' % pid]
    if say:
        s.append('                <action>coop_soc_hunter.say_%s</action>' % text)
    s.append('                <text>coop_soc_hunter_%s</text>' % text if text else '                <text />')
    s += ['                <precondition>coop_soc_hunter.%s</precondition>' % p for p in pre]
    s += ['                ' + e for e in extra]
    if brk:
        s.append('                <action>dialogs.break_dialog</action>')
    s += ['                <next>%s</next>' % n for n in nxt]
    s.append('            </phrase>')
    return s


def redirect(pid, pre, nxt):
    return ['            <phrase id="%s">' % pid, '                <text />', '                <precondition>coop_soc_hunter.%s</precondition>' % pre,
            '                <next>%s</next>' % nxt, '            </phrase>']


# ---- SoC bar_bar_hunter_start: the hunter's greeting (state: problem / waiting for the rifle / thanks)
H1 = ['    <dialog id="bar_soc_hunter_start_dialog">', '        <phrase_list>',
      '            <!-- original SoC bar_bar_hunter_start; the greeting is chosen by the state of the rifle quest -->',
      '            <phrase id="0">', '                <text />']
H1 += ['                <next>%s</next>' % n for n in ('1', '2', '3')]
H1 += ['            </phrase>']
H1 += redirect('1', 'st_new', '11') + ph('11', 'problem')
H1 += redirect('2', 'st_wait', '21') + ph('21', 'news')
H1 += redirect('3', 'st_done', '31') + ph('31', 'thanks')
H1 += ['        </phrase_list>', '    </dialog>']

# ---- SoC bar_bar_hunter_quest_start: "Go on." -> the offer -> accept (starts bar_hunter_rifle) / refuse
H2 = ['    <dialog id="bar_soc_hunter_quest_dialog">', '        <dont_has_flag>%s</dont_has_flag>' % ACCEPT, '        <phrase_list>',
      '            <!-- original SoC bar_bar_hunter_quest_start; accepting sets the mod flag that gives the task -->']
H2 += ph('0', 'q_0', ['1'])
H2 += ph('1', 'q_1', ['11', '12'])
H2 += ph('11', 'q_11', ['111'], extra=['<give_flag>%s</give_flag>' % ACCEPT])
H2 += ph('111', 'q_111', ['1111'])
H2 += ph('1111', 'q_1111', brk=True)
H2 += ph('12', 'q_12', ['121'])
H2 += ph('121', 'q_121', ['1212'])
H2 += ph('1212', 'q_1212', brk=True)
H2 += ['        </phrase_list>', '    </dialog>']

# ---- SoC bar_bar_hunter_quest_finish: the rifle is taken, 4000, the flag that completes the return step
H3 = ['    <dialog id="bar_soc_hunter_finish_dialog">', '        <has_flag>%s</has_flag>' % ACCEPT, '        <dont_has_flag>%s</dont_has_flag>' % DONE,
      '        <precondition>coop_soc_hunter.has_rifle</precondition>', '        <phrase_list>',
      '            <!-- original SoC bar_bar_hunter_quest_finish; rifle, money and flag in the SAME phrase so a cut-off talk cannot lose any of them -->']
H3 += ph('0', 'f_0', ['1'], extra=['<action>coop_soc_hunter.take_rifle</action>', '<action>coop_soc_hunter.reward</action>',
                                   '<give_flag>%s</give_flag>' % DONE])
H3 += ph('1', 'f_1', brk=True)
H3 += ['        </phrase_list>', '    </dialog>']
NEW = b''.join(x.encode('ascii') + NL for x in H1 + H2 + H3)

OLD = ('bar_smart_terrain_1_stalker_barmen_go_to_military_dialog',
       'bar_smart_terrain_1_stalker_informant_the_meeting_place_cannot_be_changed_dialog',
       'bar_smart_terrain_1_stalker_bad_hunter_start_dialog',
       'bar_smart_terrain_1_stalker_bad_hunter_find_the_family_gun_quest_dialog',
       'bar_smart_terrain_1_stalker_bad_hunter_find_the_family_gun_quest_idle_dialog')


def bar(data):
    for d in OLD + ('bar_soc_hunter_start_dialog', 'bar_soc_hunter_quest_dialog', 'bar_soc_hunter_finish_dialog'):
        data = drop_dialog(data, d)
    i = data.rindex(b'</game_dialogs>')
    return data[:i] + NEW + data[i:]


rw(P('quest_dialogs', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l05_bar.xml'), bar)


# ---- characters
def chars(data):
    m = re.search(rb'<specific_character id="bar_smart_terrain_1_stalker_barmen".*?</specific_character>', data, re.S)
    blk = re.sub(rb'[ \t]*<actor_dialog>bar_smart_terrain_1_stalker_barmen_go_to_military_dialog</actor_dialog>[ \t]*\r?\n', b'', m.group(0))
    data = data[:m.start()] + blk + data[m.end():]
    m = re.search(rb'<specific_character id="bar_smart_terrain_1_stalker_bad_hunter".*?</specific_character>', data, re.S)
    blk = m.group(0)
    blk = blk.replace(b'<start_dialog>bar_smart_terrain_1_stalker_bad_hunter_start_dialog</start_dialog>', b'<start_dialog>bar_soc_hunter_start_dialog</start_dialog>')
    blk = blk.replace(b'<actor_dialog>bar_smart_terrain_1_stalker_bad_hunter_find_the_family_gun_quest_dialog</actor_dialog>',
                      b'<actor_dialog>bar_soc_hunter_quest_dialog</actor_dialog>')
    blk = blk.replace(b'<actor_dialog>bar_smart_terrain_1_stalker_bad_hunter_find_the_family_gun_quest_idle_dialog</actor_dialog>',
                      b'<actor_dialog>bar_soc_hunter_finish_dialog</actor_dialog>')
    return data[:m.start()] + blk + data[m.end():]


rw(P('repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l05_bar.xml'), chars)

# ---- hidden tasks
HIDDEN = ['ros_start_go_to_yantar_quest_task',
          'bar_start_the_meeting_place_cannot_be_changed_1_quest_task',
          'bar_start_the_meeting_place_cannot_be_changed_2_quest_task',
          'bar_start_the_meeting_place_cannot_be_changed_3_quest_task']
HEAD = ('; Bar and Rostok (patch bar_soc_quests): "The meeting place cannot be changed" x3 is a mod-only story (the informant dialog that started it is gone);\r\n'
        '; ros_start_go_to_yantar repeated the Bar task: SoC has ONE task bar_x16_documents (bar_start_go_to_yantar_quest_task, its text and marker follow the objectives).\r\n')


def hidden(data):
    have = set(l.strip() for l in data.decode('cp1251', errors='replace').splitlines())
    add = [h for h in HIDDEN if h not in have]
    if not add:
        return data
    if not data.endswith(b'\n'):
        data += NL
    return data + NL + HEAD.encode('ascii') + NL.join(a.encode('ascii') for a in add) + NL


rw(P('repeatable_quests', 'gamedata', 'configs', 'misc', 'coop_hidden_tasks.ltx'), hidden)

print('changed:', changed if changed else 'nothing (already applied)')
