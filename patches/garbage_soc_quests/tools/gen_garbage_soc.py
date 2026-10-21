"""Makes (idempotent) every config edit of patch garbage_soc_quests. Offline, seconds.
  python patches\\garbage_soc_quests\\tools\\gen_garbage_soc.py <mod source dir (has gamedata.db0)>

Files it writes (all bytes are kept except the edited lines; ASCII edits only):
  this patch      configs\\misc\\tm_coop_l02_garbage.ltx                  (the mod's file: Seriy task text/target, boar reward moved, the report task)
                  configs\\scripts\\coop_l02_garbage\\gar_smart_terrain_9_walker_prapor.ltx   (the commander can be talked to)
                  configs\\text\\eng|rus\\st_garbage_soc_quests.xml          (SoC phrases of Seriy and the Duty commander, the report task text)
  campfires       gar_smart_terrain_7_walker_gray.ltx, gar_smart_terrain_2_walker_devil.ltx   (Seriy and Bes wait for the arrival, not for the Yurik / Bes steps)
  garbage_duty    dialogs_coop_l02_garbage.xml (Seriy dialogs, the commander dialog), character_desc_coop_l02_garbage.xml (second Seriy dialog)
  repeatable_quests  configs\\misc\\coop_hidden_tasks.ltx (+1 id)
Run it again after the mod's files or one of those patches change."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PATCH))
P = os.path.join(REPO, 'patches')
MOD = sys.argv[1]
MODCFG = os.path.join(MOD, 'gamedata.db0', 'configs')


def rd(path):
    return open(path, 'rb').read().decode('latin-1')


def wr(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(text.encode('latin-1'))


def report(name, changed):
    print(('changed  ' if changed else 'unchanged') + ' ' + name)


def set_key(text, section, key, value):
    """rewrite 'key = value' inside [section]; value None deletes the line. Returns new text."""
    m = re.search(r'^\[' + re.escape(section) + r'\][^\n]*\n', text, re.M)
    assert m, 'section ' + section
    end = re.search(r'^\[', text[m.end():], re.M)
    stop = m.end() + end.start() if end else len(text)
    body = text[m.end():stop]
    pat = re.compile(r'^' + re.escape(key) + r'[ \t]*=[^\r\n]*(\r?\n)?', re.M)
    nl = '\r\n' if '\r\n' in body else '\n'
    if value is None:
        body = pat.sub('', body)
    elif pat.search(body):
        body = pat.sub(lambda mm: key + ' = ' + value + (mm.group(1) or ''), body, count=1)
    else:
        body = body.rstrip('\r\n') + nl + key + ' = ' + value + nl
    return text[:m.end()] + body + text[stop:]


# ------------------------------------------------------------------ SoC texts
with open(os.path.join(HERE, 'soc_texts.json'), encoding='utf-8') as f:
    SOC = json.load(f)
EXTRA = {
    'st_gar_soc_duty_report_task_descr': {'eng': 'Talk with the Duty commander', 'rus': 'Поговорить с командиром заставы'},
}


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;')


def write_strings():
    ch = False
    for lang in ('eng', 'rus'):
        lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
        for sid, tx in list(SOC.items()) + list(EXTRA.items()):
            lines.append('\t<string id="%s"><text>%s</text></string>' % (sid, esc(tx[lang])))
        lines.append('</string_table>')
        data = ('\r\n'.join(lines) + '\r\n').encode('cp1251')
        path = os.path.join(PATCH, 'gamedata', 'configs', 'text', lang, 'st_garbage_soc_quests.xml')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        old = open(path, 'rb').read() if os.path.exists(path) else None
        if old != data:
            open(path, 'wb').write(data)
            ch = True
    report('configs\\text\\{eng,rus}\\st_garbage_soc_quests.xml', ch)


# ------------------------------------------------------------------ tm_coop_l02_garbage.ltx
TM_NOTE = """
;--------------------------------------------------------------------------------------------------------------------------------------
;-- Garbage in the order of the original SoC (patch garbage_soc_quests). All tasks below are handed to EVERY player by the server tick of
;-- coop_scn_garbage_soc.script (the effects %=give_task()% only reach the first player).
;--   gar_start_talk_to_gray_quest_task   SoC garbage_meet_stalker: ONE task. Given by Fox on Cordon (his dialog) or on the arrival at the Garbage.
;--                                       Text and marker follow the objective: Fox's briefing until the group is on the Garbage, then
;--                                       "Learn something of Strelok from Seriy" with Seriy's marker. The level maker's step "help the Gray
;--                                       fight off the bandits" (gar_start_help_the_gray_to_fight_off_the_bandits_quest_task) is never given.
;--   gar_start_go_to_the_agroprom_quest_task   SoC agr_meet_krot_band objective 0: given when Seriy's dialog is over.
;--   Seriy (2500) and Bes (2000) pay in the last phrase of their dialogs as in SoC, to the talking player (no reward_money here any more).
;--   gar_soc_duty_report_task            SoC gar_kill_boars objective 2 "Talk with the Duty commander": given when the boars are dead and a
;--                                       player killed one (no kill: SoC gar_actor_looser, the commander only rebukes), done by the
;--                                       commander's dialog, which also pays the reward.
;--------------------------------------------------------------------------------------------------------------------------------------
"""

TM_REPORT = """
;Квест Долга (SoC gar_kill_boars, задача 2: поговорить с командиром заставы)
[gar_soc_duty_report_task]
icon 												= ui_inGame2_gar_start_help_fight_off_the_mutants_quest_task
prior 												= 200
storyline 											= true
title 												= st_gar_start_help_fight_off_the_mutants_quest_task_name
descr 												= st_gar_soc_duty_report_task_descr
target 												= gar_smart_terrain_8_duty_prapor
condlist_0 											= {+GAR_SOC_DUTY_REPORT_INFO} complete
"""


def make_tm():
    src = rd(os.path.join(MODCFG, 'misc', 'tm_coop_l02_garbage.ltx'))
    t = src
    nl = '\r\n'
    t = set_key(t, 'gar_start_talk_to_gray_quest_task', 'descr',
                '{+GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO} st_gar_start_talk_to_gray_quest_task_descr, st_gar_start_help_the_gray_to_fight_off_the_bandits_quest_task_descr')
    t = set_key(t, 'gar_start_talk_to_gray_quest_task', 'target', '{+GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO} gar_smart_terrain_2_stalker_gray')
    t = set_key(t, 'gar_start_help_fight_off_the_mutants_quest_task', 'reward_money', None)
    # SoC pays Seriy (2500) and Bes (2000) in their dialogs (coop_scn_garbage_soc.pay_seriy / pay_bes), to the talking player
    t = set_key(t, 'gar_start_talk_to_gray_quest_task', 'reward_money', None)
    t = set_key(t, 'gar_start_talk_to_devil_1_quest_task', 'reward_money', None)
    t = t.rstrip('\r\n') + nl
    t += TM_NOTE.replace('\n', nl)
    # the mod's file is UTF-8 (Russian comments): the comment of the new section is written as UTF-8 bytes
    t += TM_REPORT.replace('\n', nl).encode('utf-8').decode('latin-1')
    path = os.path.join(PATCH, 'gamedata', 'configs', 'misc', 'tm_coop_l02_garbage.ltx')
    old = rd(path) if os.path.exists(path) else None
    wr(path, t)
    report('configs\\misc\\tm_coop_l02_garbage.ltx', old != t)


# ------------------------------------------------------------------ the Duty commander can be talked to
def make_prapor():
    src = rd(os.path.join(MODCFG, 'scripts', 'coop_l02_garbage', 'gar_smart_terrain_9_walker_prapor.ltx'))
    t = set_key(src, 'walker@gar_smart_terrain_9_walker_prapor', 'meet', 'meet@gar_smart_terrain_9_prapor')
    nl = '\r\n' if '\r\n' in src else '\n'
    t = t.rstrip('\r\n') + nl + nl + '\n'.join([
        '[meet@gar_smart_terrain_9_prapor]',
        'close_snd_hello = nil', 'close_snd_bye = nil', 'close_anim = nil', 'close_victim = nil', 'far_anim = nil', 'far_victim = nil',
        'close_distance = 0', 'far_distance = 0', 'close_snd_distance = 5', 'abuse = false',
        'use = {=actor_enemy} false, true', 'allow_break = true', 'meet_on_talking = false', 'trade_enable = false', ''
    ]).replace('\n', nl)
    path = os.path.join(PATCH, 'gamedata', 'configs', 'scripts', 'coop_l02_garbage', 'gar_smart_terrain_9_walker_prapor.ltx')
    old = rd(path) if os.path.exists(path) else None
    wr(path, t)
    report('scripts\\coop_l02_garbage\\gar_smart_terrain_9_walker_prapor.ltx', old != t)


# ------------------------------------------------------------------ campfires: Seriy and Bes wait for the arrival
def edit_gray():
    path = os.path.join(P, 'campfires', 'gamedata', 'configs', 'scripts', 'coop_l02_garbage', 'gar_smart_terrain_7_walker_gray.ltx')
    t = rd(path)
    if 'GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO' in t:
        return report('campfires gar_smart_terrain_7_walker_gray.ltx', False)
    m1 = re.search(r'^on_info[ \t]*=[ \t]*\{-GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO \+GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO\}[^\r\n]*', t, re.M)
    m2 = re.search(r'^on_info2[ \t]*=[ \t]*\{\+GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO \+GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO\}[^\r\n]*', t, re.M)
    assert m1 and m2, 'gray initial state lines not found'
    t = t[:m1.start()] + 'on_info = {-GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO +GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO} walker@gar_smart_terrain_7_walker_gray_idle %=scenario_autosave(st_help_the_gray_to_fight_off_the_bandits)%' + t[m1.end():]
    m2 = re.search(r'^on_info2[ \t]*=[ \t]*\{\+GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO \+GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO\}[^\r\n]*', t, re.M)
    t = t[:m2.start()] + 'on_info2 = {+GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO} kamp@gar_smart_terrain_7_animpoint_1_no_meet' + t[m2.end():]
    wr(path, t)
    report('campfires gar_smart_terrain_7_walker_gray.ltx', True)


def edit_devil():
    path = os.path.join(P, 'campfires', 'gamedata', 'configs', 'scripts', 'coop_l02_garbage', 'gar_smart_terrain_2_walker_devil.ltx')
    t = rd(path)
    if 'GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO' in t:
        return report('campfires gar_smart_terrain_2_walker_devil.ltx', False)
    m1 = re.search(r'^on_info[ \t]*=[ \t]*\{-GAR_SMART_TERRAIN_2_WALKER_DEVIL_AMBUSH_INFO \+GAR_SMART_TERRAIN_1_STALKER_YURIK_SQUAD_DEAD\}[^\r\n]*', t, re.M)
    assert m1, 'devil initial state line not found'
    t = t[:m1.start()] + 'on_info = {-GAR_SMART_TERRAIN_2_WALKER_DEVIL_AMBUSH_INFO +GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO} walker@gar_smart_terrain_2_walker_devil_idle' + t[m1.end():]
    m2 = re.search(r'^on_info2[ \t]*=[ \t]*\{-GAR_SMART_TERRAIN_2_WALKER_DEVIL_AMBUSH_INFO \+GAR_SMART_TERRAIN_1_BANDIT_1_SQUAD_DEAD\}[^\r\n]*(\r?\n)?', t, re.M)
    assert m2, 'devil second line not found'
    t = t[:m2.start()] + t[m2.end():]
    wr(path, t)
    report('campfires gar_smart_terrain_2_walker_devil.ltx', True)


# ------------------------------------------------------------------ garbage_duty: dialogs
def block(text, did):
    m = re.search(r'[ \t]*<dialog id="' + re.escape(did) + r'">.*?</dialog>[ \t]*(\r?\n)?', text, re.S)
    assert m, 'dialog ' + did
    return m


GRAY_START = """    <dialog id="gar_smart_terrain_2_stalker_gray_start_dialog">
        <phrase_list>
            <phrase id="0">
                <action>coop_scn_garbage_soc.say_seriy_22</action>
                <text>gar_seriy_start_22</text>
            </phrase>
        </phrase_list>
    </dialog>
"""


def gray_help(did, extra_cond, ids, fn):
    a, b, c = ids
    return """    <dialog id="%s">
        <has_flag>GAR_SMART_TERRAIN_6_BANDIT_1_SQUAD_DEAD</has_flag>
        <has_flag>GAR_SMART_TERRAIN_6_BANDIT_2_SQUAD_DEAD</has_flag>
        <dont_has_flag>GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO</dont_has_flag>
        %s
        <phrase_list>
            <phrase id="0">
                <action>coop_scn_garbage_soc.say_seriy_%s</action>
                <text>gar_seriy_start_%s</text>
                <next>1</next>
            </phrase>
            <phrase id="1">
                <action>coop_scn_garbage_soc.say_seriy_%s</action>
                <text>gar_seriy_start_%s</text>
                <next>2</next>
            </phrase>
            <phrase id="2">
                <action>coop_scn_garbage_soc.say_seriy_%s</action>
                <text>gar_seriy_start_%s</text>
                <action>coop_scn_garbage_soc.pay_seriy</action>
                <action>dialogs.break_dialog</action>
                <give_flag>GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO</give_flag>
            </phrase>
        </phrase_list>
    </dialog>
""" % (did, extra_cond, a, a, b, b, c, c)


DUTY = """    <dialog id="gar_duty_pass_start_dialog">
        <phrase_list>
            <phrase id="0">
                <text />
                <next>2</next>
                <next>1</next>
                <next>3</next>
            </phrase>
            <!-- the boar wave is over and a player killed a boar (SoC gar_kill_boars objective 2): the commander thanks him, the report completes the task, the reward is his -->
            <phrase id="2">
                <precondition>coop_scn_garbage_soc.report_open</precondition>
                <action>coop_scn_garbage_soc.say_duty_1231</action>
                <text>gar_dolg_blokpost_1231</text>
                <next>12311</next>
            </phrase>
            <phrase id="12311">
                <action>coop_scn_garbage_soc.say_duty_12311</action>
                <action>coop_scn_garbage_soc.report_pay</action>
                <text>gar_dolg_blokpost_12311</text>
            </phrase>
            <phrase id="1">
                <precondition>coop_scn_garbage_duty.pass_closed</precondition>
                <text />
                <next>11</next>
            </phrase>
            <phrase id="11">
                <action>coop_pda_phrases.say__gar_smart_terrain_8_duty_prapor_start_dialog_0</action>
                <text>gar_smart_terrain_8_duty_prapor_start_dialog_0</text>
                <next>111</next>
            </phrase>
            <phrase id="111">
                <action>coop_pda_phrases.say__gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_0</action>
                <text>gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_0</text>
                <next>1111</next>
            </phrase>
            <phrase id="1111">
                <action>coop_pda_phrases.say__gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_1</action>
                <text>gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_1</text>
                <next>11111</next>
                <next>11112</next>
                <next>1111211</next>
                <next>1111212</next>
                <next>111122</next>
            </phrase>
            <phrase id="11111">
                <precondition>coop_scn_garbage_duty.case_missing</precondition>
                <text>gar_duty_pass_i_see</text>
                <next>111111</next>
            </phrase>
            <phrase id="111111">
                <text>gar_duty_pass_rules</text>
            </phrase>
            <phrase id="11112">
                <action>coop_pda_phrases.say__gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_2</action>
                <precondition>coop_scn_garbage_duty.case_have</precondition>
                <text>gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_2</text>
                <next>111121</next>
            </phrase>
            <phrase id="111121">
                <action>coop_pda_phrases.say__gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_3</action>
                <action>coop_scn_garbage_duty.give_pass_case</action>
                <text>gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_3</text>
                <next>123</next>
            </phrase>
            <phrase id="123">
                <action>coop_pda_phrases.say__gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_4</action>
                <text>gar_smart_terrain_8_duty_prapor_the_destination_is_a_bar_4</text>
                <next>33</next>
            </phrase>
            <phrase id="1111211">
                <precondition>coop_scn_garbage_duty.can_pay</precondition>
                <action>coop_scn_garbage_duty.give_pass_money</action>
                <text>gar_duty_pass_pay</text>
                <next>11112111</next>
            </phrase>
            <phrase id="11112111">
                <text>gar_duty_pass_paid</text>
            </phrase>
            <!-- SoC "What's the favor?": kill the boars, the passage is paid (the wave is the one of the Duty zone; the pass comes with a won wave, patch garbage_duty) -->
            <phrase id="1111212">
                <precondition>coop_scn_garbage_soc.favor_open</precondition>
                <action>coop_scn_garbage_soc.say_duty_1111212</action>
                <text>gar_dolg_blokpost_1111212</text>
                <next>11112121</next>
            </phrase>
            <phrase id="11112121">
                <action>coop_scn_garbage_soc.say_duty_11112121</action>
                <text>gar_dolg_blokpost_11112121</text>
                <next>111121211</next>
            </phrase>
            <phrase id="111121211">
                <action>coop_scn_garbage_soc.say_duty_111121211</action>
                <action>coop_scn_garbage_soc.favor_start</action>
                <text>gar_dolg_blokpost_111121211</text>
                <next>1111212111</next>
            </phrase>
            <phrase id="1111212111">
                <action>coop_scn_garbage_soc.say_duty_1111212111</action>
                <text>gar_dolg_blokpost_1111212111</text>
            </phrase>
            <phrase id="111122">
                <precondition>coop_scn_garbage_duty.cannot_pay</precondition>
                <text>gar_duty_pass_no_money</text>
                <next>111123</next>
            </phrase>
            <phrase id="111123">
                <text>gar_duty_pass_no_pass</text>
            </phrase>
            <phrase id="3">
                <precondition>coop_scn_garbage_duty.pass_open</precondition>
                <text />
                <next>33</next>
            </phrase>
            <phrase id="33">
                <text>gar_duty_pass_say_hi</text>
            </phrase>
        </phrase_list>
    </dialog>
"""


def edit_dialogs():
    path = os.path.join(P, 'garbage_duty', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l02_garbage.xml')
    t = rd(path)
    nl = '\r\n' if t.count('\r\n') >= t.count('\n') / 2 else '\n'
    new = t
    if 'coop_scn_garbage_soc.say_seriy_22</action>' not in new:
        m = block(new, 'gar_smart_terrain_2_stalker_gray_start_dialog')
        new = new[:m.start()] + GRAY_START.replace('\n', nl) + new[m.end():]
    if 'gar_smart_terrain_2_stalker_gray_help_nofox' not in new:
        m = block(new, 'gar_smart_terrain_2_stalker_gray_help')
        fox = gray_help('gar_smart_terrain_2_stalker_gray_help', '<has_flag>ESC_SMART_TERRAIN_6_STALKER_FOX_INFO_MILITARY_STOP_DIALOG_INFO</has_flag>', ('221', '2211', '2212'), None)
        nofox = gray_help('gar_smart_terrain_2_stalker_gray_help_nofox', '<dont_has_flag>ESC_SMART_TERRAIN_6_STALKER_FOX_INFO_MILITARY_STOP_DIALOG_INFO</dont_has_flag>', ('222', '2221', '2222'), None)
        new = new[:m.start()] + (fox + nofox).replace('\n', nl) + new[m.end():]
    # SoC pays in the last phrase (once per talking player, see coop_scn_garbage_soc.pay_once)
    for did in ('gar_smart_terrain_2_stalker_gray_help', 'gar_smart_terrain_2_stalker_gray_help_nofox'):
        m = block(new, did)
        if 'pay_seriy' not in m.group(0):
            blk = m.group(0).replace('<action>dialogs.break_dialog</action>', '<action>coop_scn_garbage_soc.pay_seriy</action>' + nl + '                <action>dialogs.break_dialog</action>', 1)
            new = new[:m.start()] + blk + new[m.end():]
    m = block(new, 'gar_smart_terrain_4_stalker_devil_help_the_and')
    if 'pay_bes' not in m.group(0):
        blk = m.group(0).replace('<text>gar_smart_terrain_4_stalker_devil_help_the_and_2</text>', '<text>gar_smart_terrain_4_stalker_devil_help_the_and_2</text>' + nl + '                <action>coop_scn_garbage_soc.pay_bes</action>', 1)
        assert blk != m.group(0)
        new = new[:m.start()] + blk + new[m.end():]
    if 'coop_scn_garbage_soc.report_open' not in new:
        m = block(new, 'gar_duty_pass_start_dialog')
        new = new[:m.start()] + DUTY.replace('\n', nl) + new[m.end():]
    wr(path, new)
    report('garbage_duty dialogs_coop_l02_garbage.xml', new != t)

    cpath = os.path.join(P, 'garbage_duty', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l02_garbage.xml')
    c = rd(cpath)
    if 'gar_smart_terrain_2_stalker_gray_help_nofox' not in c:
        mm = re.search(r'([ \t]*)<actor_dialog>gar_smart_terrain_2_stalker_gray_help</actor_dialog>[^\r\n]*(\r?\n)', c)
        assert mm
        c = c[:mm.end()] + mm.group(1) + '<actor_dialog>gar_smart_terrain_2_stalker_gray_help_nofox</actor_dialog>' + mm.group(2) + c[mm.end():]
        wr(cpath, c)
        report('garbage_duty character_desc_coop_l02_garbage.xml', True)
    else:
        report('garbage_duty character_desc_coop_l02_garbage.xml', False)


# ------------------------------------------------------------------ hidden task
def edit_hidden():
    path = os.path.join(P, 'repeatable_quests', 'gamedata', 'configs', 'misc', 'coop_hidden_tasks.ltx')
    t = rd(path)
    tid = 'gar_start_help_the_gray_to_fight_off_the_bandits_quest_task'
    if tid in t:
        return report('repeatable_quests coop_hidden_tasks.ltx', False)
    nl = '\r\n' if '\r\n' in t else '\n'
    m = re.search(r'^gar_start_talk_to_yurik_quest_task[^\r\n]*(\r?\n)', t, re.M)
    assert m
    t = t[:m.end()] + tid + nl + t[m.end():]
    wr(path, t)
    report('repeatable_quests coop_hidden_tasks.ltx', True)


write_strings()
make_tm()
make_prapor()
edit_gray()
edit_devil()
edit_dialogs()
edit_hidden()
