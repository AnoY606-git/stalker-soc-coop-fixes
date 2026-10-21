"""Changes of files that OTHER patches ship (idempotent: a second run changes nothing).  Run it after the release zip is built / before build.py:

  python -I patches\\soc_yan_semenov\\tools\\apply_shared.py [<repo root>]

<repo root> defaults to the repo this script lives in. Tests run it on a COPY of the repo (scratch dir), never on the live tree while a release is built.

  1. patches\\quest_dialogs\\...\\dialogs_coop_l08_yantar.xml
       - Sakharov (yan_soc_saharov_dialog): the Kruglov offer needs a living professor (SoC 21112), a dead professor gives the Semenov offer
         (SoC 21113 / 211131 / 211132), new branch 5 (Semenov died: prototype anyway), the results branch yields to it
       - Kruglov (yan_soc_kruglov_dialog): his states yield while the professor is dead, new branch 6 ("no time")
       - new dialogs yan_soc_semenov_dialog (SoC yantar_help_scientist for Semenov) and yan_soc_wounded_dialog (SoC yantar_wounded_scientist)
  2. patches\\repeatable_quests\\...\\character_desc_coop_l08_yantar.xml   specific character yan_soc_semenov (SoC yan_Semenov)
  3. patches\\cordon_technician and patches\\freedom_duty \\...\\npc_profile_addon.xml   profile yan_soc_semenov
  4. patches\\yantar_restore\\...\\spawn_sections_coop_l08_yantar.ltx   sections yan_soc_semenov (bunker) and yan_soc_semenov_wounded
  5. patches\\soc_yan_x16_quests\\...\\tm_coop_l08_yantar.ltx   the measurement task follows the Semenov variant (text, marker), fails when the
     scientist dies before the talk; new task yan_soc_return_task (SoC yan_scientist_return_task)
  6. installer\\changes_1.4.en|ru.txt and changes_1.4.1.en|ru.txt   one line
  7. patches\\soc_yan_x16_quests\\NOTES.md   a pointer to this patch
"""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.dirname(here)
repo = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(patch))
repo = os.path.abspath(repo)
P = lambda *a: os.path.join(repo, 'patches', *a)
changed = []
CRLF = '\r\n'


def rw(path, fn, enc='latin-1'):
    if not os.path.exists(path):
        print('MISSING', os.path.relpath(path, repo))
        return
    data = open(path, 'rb').read().decode(enc)
    new = fn(data)
    if new != data:
        open(path, 'wb').write(new.encode(enc))
        changed.append(os.path.relpath(path, repo))


def nl_of(text):
    return CRLF if text.count('\r\n') * 2 >= text.count('\n') else '\n'


# flags (coop_soc_yan_semenov.script, section F)
OFFERED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO'
PREP = 'YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO'
REPORTED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO'
HELMET = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO'
M1, M2, M3 = ('YAN_START_TAKE_MEASUREMENTS_%d_QUEST_TASK_INFO' % i for i in (1, 2, 3))
SEM_START = 'YAN_FIND_SCIENTIST_SEMENOV_START'
WOUNDED, WGONE = 'YAN_SOC_SEM_WOUNDED', 'YAN_SOC_SEM_WOUNDED_GONE'
TALKED, DIE = 'YAN_SCIENTIST_RETURN_TO_BUNKER', 'YAN_SCIENTIST_DIE'
RET = 'YAN_SCIENTIST_RETURN_TASK'
MOD = 'coop_soc_yan_semenov'


# ---------------------------------------------------------------------------------------------------
# 1. dialogs
# ---------------------------------------------------------------------------------------------------
def ph(kind, pid, nxt=(), pre=(), flags=(), end=False, indent='            '):
    s = [indent + '<phrase id="%s">' % pid,
         indent + '    <action>%s.say_%s%s</action>' % (MOD, kind, pid),
         indent + '    <text>coop_soc_yan_sem_%s_%s</text>' % (kind, pid)]
    s += [indent + '    <precondition>%s.%s</precondition>' % (MOD, p) for p in pre]
    s += [indent + '    <give_flag>%s</give_flag>' % f for f in flags]
    if end:
        s.append(indent + '    <action>dialogs.break_dialog</action>')
    s += [indent + '    <next>%s</next>' % n for n in nxt]
    s.append(indent + '</phrase>')
    return s


def redirect(pid, pre, nxt, indent='            '):
    return [indent + '<phrase id="%s">' % pid, indent + '    <text />', indent + '    <precondition>%s.%s</precondition>' % (MOD, pre),
            indent + '    <next>%s</next>' % nxt, indent + '</phrase>']


def sakharov_new():
    s = []
    # SoC 21113 / 211131 / 211132: the offer when the professor is dead (21112 / 211121 / 2111211 are the Kruglov ones)
    s += ph('s', '21113', ['211131'], pre=['st_prof_die'])
    s += ph('s', '211131', ['211132'])
    s += ph('s', '211132', flags=[OFFERED, SEM_START], end=True)
    # SoC branch 5: Semenov died (not talked to Sakharov yet): the prototype anyway. The flags are in the FIRST phrase so that a cut-off talk
    # cannot lose them (the helmet is handed out by the tick of coop_soc_yan, the lab job starts)
    s += redirect('5', 'st_s_semdead', '51')
    s += ph('s', '51', ['511'], flags=[REPORTED, HELMET])
    s += ph('s', '511', ['5111'])
    s += ph('s', '5111', ['51111'])
    s += ph('s', '51111', ['511111'])
    s += ph('s', '511111', ['5111111'])
    s += ph('s', '5111111', ['511111111'])
    s += ph('s', '511111111', ['51112'])
    s += ph('s', '51112', ['51113'])
    s += ph('s', '51113', ['51114'])
    s += ph('s', '51114', end=True)
    return s


def semenov_dialog():
    d = ['    <dialog id="yan_soc_semenov_dialog">', '        <phrase_list>',
         '            <!-- original SoC yantar_help_scientist for Semenov: no time before the offer, the escort talk (the device is handed out by the tick of coop_soc_yan) -->',
         '            <phrase id="0">', '                <text />']
    d += ['                <next>%s</next>' % n for n in ('6', '5', '10', '7')]
    d += ['            </phrase>']
    d += redirect('6', 'st_m_meet', '61') + ph('m', '61')
    d += redirect('5', 'st_m_talk', '51')
    d += ph('m', '51', ['511']) + ph('m', '511', ['512']) + ph('m', '512', ['513'])
    d += ph('m', '513', ['514'], flags=[PREP]) + ph('m', '514', ['515']) + ph('m', '515', end=True)
    d += redirect('10', 'st_m_busy', '101') + ph('m', '101')
    d += redirect('7', 'st_m_after', '71') + ph('m', '71')
    d += ['        </phrase_list>', '    </dialog>']
    return d


def wounded_dialog():
    d = ['    <dialog id="yan_soc_wounded_dialog">', '        <phrase_list>',
         '            <!-- original SoC yantar_wounded_scientist (help_start_dialog of the wounded scientist) -->',
         '            <phrase id="0">', '                <text />']
    d += ['                <next>%s</next>' % n for n in ('1', '2', '3')]
    d += ['            </phrase>']
    d += redirect('1', 'st_w_first', '11') + ph('w', '11', ['111']) + ph('w', '111', flags=[TALKED], end=True)
    d += redirect('2', 'st_w_done', '211') + ph('w', '211')
    d += redirect('3', 'st_w_after', '31') + ph('w', '31')
    d += ['        </phrase_list>', '    </dialog>']
    return d


def dialog_span(t, did):
    a = t.find('<dialog id="%s">' % did)
    if a < 0:
        return None
    b = t.find('</dialog>', a) + len('</dialog>')
    return a, b


def edit_dialogs(t):
    nl = nl_of(t)
    # --- Sakharov
    sp = dialog_span(t, 'yan_soc_saharov_dialog')
    assert sp, 'yan_soc_saharov_dialog missing (run quest_dialogs\\tools\\apply_dialogs.py first)'
    a, b = sp
    blk = t[a:b]
    if 'st_s_semdead' not in blk:
        # root: branch 5 (Semenov died) next to branch 3
        blk = blk.replace('<next>3</next>' + nl, '<next>3</next>' + nl + '                <next>5</next>' + nl, 1)
        # results yield to branch 5
        blk, n = re.subn(r'(<phrase id="3">.*?<precondition>)coop_soc_yan\.st_s_results(</precondition>)', r'\1' + MOD + r'.st_s_results\2', blk, count=1, flags=re.S)
        assert n == 1, 'phrase 3 of the Sakharov dialog'
        # the Kruglov offer needs a living professor, the Semenov offer follows it
        blk, n = re.subn(r'(<phrase id="21111">.*?<next>21112</next>)', r'\1' + nl + '                <next>21113</next>', blk, count=1, flags=re.S)
        assert n == 1, 'phrase 21111'
        blk, n = re.subn(r'(<phrase id="21112">\s*<action>[^<]*</action>\s*<text>[^<]*</text>)',
                         r'\1' + nl + '                <precondition>' + MOD + '.st_prof_alive</precondition>', blk, count=1)
        assert n == 1, 'phrase 21112'
        add = nl.join(sakharov_new()) + nl
        i = blk.rfind('        </phrase_list>')
        assert i > 0
        blk = blk[:i] + add + blk[i:]
        t = t[:a] + blk + t[b:]
    # --- Kruglov
    sp = dialog_span(t, 'yan_soc_kruglov_dialog')
    assert sp, 'yan_soc_kruglov_dialog missing'
    a, b = sp
    blk = t[a:b]
    if 'st_k_other' not in blk:
        blk = re.sub(r'coop_soc_yan\.(st_k_(?:meet_r|meet|talk|busy|after))', MOD + r'.\1', blk)
        blk = blk.replace('<next>7</next>' + nl, '<next>7</next>' + nl + '                <next>6</next>' + nl, 1)
        add = nl.join(redirect('6', 'st_k_other', '61') + ph('m', '61')) + nl
        i = blk.rfind('        </phrase_list>')
        blk = blk[:i] + add + blk[i:]
        t = t[:a] + blk + t[b:]
    # --- new dialogs
    if 'id="yan_soc_semenov_dialog"' not in t:
        i = t.rfind('</game_dialogs>')
        assert i > 0
        t = t[:i] + nl.join(semenov_dialog() + wounded_dialog()) + nl + t[i:]
    return t


rw(P('quest_dialogs', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l08_yantar.xml'), edit_dialogs)


# ---------------------------------------------------------------------------------------------------
# 2. specific character, 3. profile
# ---------------------------------------------------------------------------------------------------
CHAR = '''<specific_character id="yan_soc_semenov" team_default = "1">
    <name>coop_soc_yan_sem_name</name>
    <icon>ui_inGame2_neutral_nauchniy</icon>
    <map_icon x="0" y="6"></map_icon>
    <bio>coop_soc_yan_sem_bio</bio>
    <class>yan_soc_semenov</class>
    <community>ecolog</community> <terrain_sect>stalker_terrain</terrain_sect>
    <money min="600" max="2000" infinitive="0"></money>
    <rank>2071</rank>
    <reputation>50</reputation>
    <visual>actors\\stalker_ecolog\\stalker_ecolog_1</visual>
    <snd_config>characters_voice\\human_03\\csky\\</snd_config>
    <crouch_type>1</crouch_type>
    <supplies>
        [spawn] \\n
        wpn_walther \\n
        ammo_9x19_fmj \\n

#include "gameplay\\character_items_nd.xml"
#include "gameplay\\character_food.xml"
#include "gameplay\\character_drugs_3.xml"
#include "gameplay\\character_drugs_sci.xml"
#include "gameplay\\character_drugs_mil.xml"
    </supplies>
    <start_dialog>yan_soc_semenov_dialog</start_dialog>
</specific_character>
'''


def edit_char(t):
    if 'id="yan_soc_semenov"' in t:
        return t
    nl = nl_of(t)
    i = t.rfind('</xml>')
    assert i > 0
    return t[:i] + CHAR.replace('\n', nl) + '  ' + t[i:]


rw(P('repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l08_yantar.xml'), edit_char)

PROFILE = '\t<character id="yan_soc_semenov">\n\t\t<class>yan_soc_semenov</class>\n\t</character>\n'


def edit_profile(t):
    if 'id="yan_soc_semenov"' in t:
        return t
    nl = nl_of(t)
    i = t.rfind('</xml>')
    assert i > 0
    return t[:i] + PROFILE.replace('\n', nl) + t[i:]


for owner in ('cordon_technician', 'freedom_duty'):
    rw(P(owner, 'gamedata', 'configs', 'gameplay', 'npc_profile_addon.xml'), edit_profile)

# ---------------------------------------------------------------------------------------------------
# 4. spawn sections
# ---------------------------------------------------------------------------------------------------
SPAWN = ''';--- soc_yan_semenov: Semenov (SoC yan_Semenov, spawn yantar_semenov) and the wounded scientist; created by scripts\\coop_soc_yan_semenov.script
[yan_soc_semenov]:stalker
$spawn						= "respawn\\yan_soc_semenov"
character_profile			= yan_soc_semenov
spec_rank					= veteran
community					= ecolog
story_id					= yan_soc_semenov
custom_data					= scripts\\coop_l08_yantar\\yan_soc_semenov.ltx

; the same man wounded at the third measurement site; the story id is the one of the SoC task markers (yan_semenov_help)
[yan_soc_semenov_wounded]:stalker
$spawn						= "respawn\\yan_soc_semenov_wounded"
character_profile			= yan_soc_semenov
spec_rank					= veteran
community					= ecolog
story_id					= yan_semenov_help
custom_data					= scripts\\coop_l08_yantar\\yan_soc_semenov_wounded.ltx
'''


def edit_spawn(t):
    if '[yan_soc_semenov]' in t:
        return t
    nl = nl_of(t)
    if not t.endswith(nl):
        t += nl
    return t + nl + SPAWN.replace('\n', nl)


rw(P('yantar_restore', 'gamedata', 'configs', 'creatures', 'spawn_sections_coop_l08_yantar.ltx'), edit_spawn)

# ---------------------------------------------------------------------------------------------------
# 5. tasks
# ---------------------------------------------------------------------------------------------------
ST = 'st_yan_start_'
DESCR = ('{+%s +%s +%s +%s +%s -%s -%s -%s} coop_soc_yan_sem_escort_descr, '
         '{+%s +%s +%s} %stalk_to_the_saharov_quest_task_descr, '
         '{+%s +%s} coop_soc_yan_sem_escort_descr, '
         '{+%s} %stake_measurements_1_quest_task_descr, '
         '{+%s} coop_soc_yan_sem_talk_descr, '
         '%stalk_to_the_kruglov_quest_task_descr') % (M1, M2, M3, SEM_START, WOUNDED, TALKED, WGONE, DIE,
                                                       M1, M2, M3, ST, SEM_START, PREP, PREP, ST, SEM_START, ST)
TARGET = ('{+%s +%s +%s +%s +%s -%s -%s -%s} yan_semenov_help, '
          '{+%s +%s +%s} yan_smart_terrain_1_ecolog_saharov, '
          '{+%s -%s} yan_start_take_measurements_1_space_restrictor, '
          '{+%s -%s} yan_start_take_measurements_2_space_restrictor, '
          '{+%s -%s} yan_start_take_measurements_3_space_restrictor, '
          '{+%s} yan_soc_semenov, '
          'yan_smart_terrain_1_ecolog_kruglov') % (M1, M2, M3, SEM_START, WOUNDED, TALKED, WGONE, DIE, M1, M2, M3,
                                                    PREP, M1, PREP, M2, PREP, M3, SEM_START)
FAIL = '{+%s -%s} fail' % (DIE, TALKED)

RETURN_TASK = '''
;--------------------------------------------------------------------------------------------------------------------------------------
;-- soc_yan_semenov: SoC yan_scientist_return_task ("Talk to Sakharov"): the scientist died before the talk at the third site; given by
;-- coop_soc_yan_semenov.script to every player 4 s after his death while the lab job has not started; done by the prototype (dialog branch 5)
;--------------------------------------------------------------------------------------------------------------------------------------
[yan_soc_return_task]
icon        = ui_inGame2_yan_start_talk_to_the_saharov_quest_task
prior       = 205
storyline   = true
title       = coop_soc_yan_sem_return_name
descr       = coop_soc_yan_sem_return_descr
target      = yan_smart_terrain_1_ecolog_saharov
condlist_0  = {+%s} complete
''' % HELMET


def edit_tm(t):
    nl = nl_of(t)
    m = re.search(r'(?m)^\[yan_start_talk_to_the_kruglov_quest_task\]\r?\n', t)
    assert m, 'task section'
    end = t.find('\n[', m.end())
    end = len(t) if end < 0 else end
    sec = t[m.start():end]
    if 'coop_soc_yan_sem_talk_descr' not in sec:
        sec, n = re.subn(r'(?m)^descr(\s*)= .*$', lambda x: 'descr' + x.group(1) + '= ' + DESCR, sec, count=1)
        assert n == 1
        sec, n = re.subn(r'(?m)^target(\s*)= .*$', lambda x: 'target' + x.group(1) + '= ' + TARGET, sec, count=1)
        assert n == 1
        if 'condlist_1' not in sec:
            sec, n = re.subn(r'(?m)^(condlist_0\s*)= (.*)$', lambda x: x.group(0) + nl + 'condlist_1  = ' + FAIL, sec, count=1)
            assert n == 1
        t = t[:m.start()] + sec + t[end:]
    if '[yan_soc_return_task]' not in t:
        if not t.endswith(nl):
            t += nl
        t += RETURN_TASK.replace('\n', nl)
    return t


rw(P('soc_yan_x16_quests', 'gamedata', 'configs', 'misc', 'tm_coop_l08_yantar.ltx'), edit_tm, enc='utf-8')

# ---------------------------------------------------------------------------------------------------
# 6. changes lines, 7. notes
# ---------------------------------------------------------------------------------------------------
LINE_EN = ('- @soc_yan_semenov,soc_yan_x16_quests,quest_dialogs,repeatable_quests,yantar_restore: Yantar: the second scientist of the original. '
           'When the Wild Territory professor was not rescued, Sakharov now sends you with the assistant Semenov (a new NPC next to the bunker, '
           'the original talk) instead of Kruglov. After the three measurements Semenov lies wounded at the last site and can be talked to; if the zombies '
           'kill him, Sakharov asks you to come back ("Talk to Sakharov" with the PDA message) and gives the prototype anyway, as in the original. '
           'The wounded scientist and his talk exist only in this Semenov variant.')
LINE_RU = ('- @soc_yan_semenov,soc_yan_x16_quests,quest_dialogs,repeatable_quests,yantar_restore: Янтарь: второй учёный оригинала. '
           'Если профессор из Дикой территории не спасён, Сахаров теперь отправляет вас с ассистентом Семёновым (новый NPC у бункера, '
           'оригинальный разговор) вместо Круглова. После трёх замеров Семёнов лежит раненый у последнего места замера, с ним можно поговорить; если его '
           'убьют зомби, Сахаров просит вернуться («Поговорить с Сахаровым», сообщение в КПК) и всё равно даёт прототип, как в оригинале. '
           'Раненый учёный и разговор с ним есть только в этом варианте с Семёновым.')


def edit_changes(line):
    def fn(t):
        if '@soc_yan_semenov' in t:
            return t
        nl = nl_of(t)
        lines = t.split(nl)
        idx = None
        for i, ln in enumerate(lines):
            if ln.startswith('- @soc_yan_x16_quests'):
                idx = i
        assert idx is not None, 'no Yantar line in the changes file'
        lines.insert(idx + 1, line)
        return nl.join(lines)
    return fn


for ver in ('1.4', '1.4.1'):
    rw(os.path.join(repo, 'installer', 'changes_%s.en.txt' % ver), edit_changes(LINE_EN), enc='utf-8')
    rw(os.path.join(repo, 'installer', 'changes_%s.ru.txt' % ver), edit_changes(LINE_RU), enc='utf-8')

NOTE = ('\n\n## Semenov variant\nThe variant with the second scientist (`yan_find_scientist_semenov`), the wounded scientist and `yan_scientist_return_task` '
        'are in patch `soc_yan_semenov` (its `tools\\apply_shared.py` edits the Sakharov / Kruglov dialogs, the measurement task text and `tm_coop_l08_yantar.ltx`). '
        'Run it again after `tools\\make_tm.py` or `apply_dialogs.py` regenerated those files.\n')


def edit_notes(t):
    if 'soc_yan_semenov' in t:
        return t
    return t.rstrip('\r\n') + NOTE.replace('\n', nl_of(t)) + nl_of(t)


rw(P('soc_yan_x16_quests', 'NOTES.md'), edit_notes, enc='utf-8')

# ---------------------------------------------------------------------------------------------------
# 8. the chain checker of patch soc_yan_x16_quests resolves dialog functions and flag setters in its own script only
# ---------------------------------------------------------------------------------------------------
def edit_checker(t):
    if 'coop_soc_yan_semenov' in t:
        return t
    nl = nl_of(t)
    a = "fns = {'coop_soc_yan': set(re.findall(r'^function\s+(\w+)', script, re.M))}"
    assert a in t, 'check_yan_chain.py: fns line'
    t = t.replace(a, a + nl + "fns['coop_soc_yan_semenov'] = set(re.findall(r'^function\s+(\w+)', read('scripts/coop_soc_yan_semenov.script'), re.M)) if 'scripts/coop_soc_yan_semenov.script' in tree else set()")
    b = "'scripts/coop_scn_agroprom_soc.script'):"
    assert b in t, 'check_yan_chain.py: setter list'
    t = t.replace(b, "'scripts/coop_scn_agroprom_soc.script', 'scripts/coop_soc_yan_semenov.script'):", 1)
    return t


rw(P('soc_yan_x16_quests', 'tools', 'check_yan_chain.py'), edit_checker, enc='utf-8')

print('changed:' if changed else 'nothing to change (already applied)')
for c in changed:
    print('  ' + c)
