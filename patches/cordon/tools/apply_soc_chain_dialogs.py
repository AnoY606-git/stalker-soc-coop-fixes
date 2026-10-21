"""Rewrite three parts of patches\\cordon\\gamedata\\configs\\gameplay\\dialogs_coop_l01_escape.xml (idempotent):
  1. esc_smart_terrain_1_trader_sidorovich_flesh      phrase 2 also sets ESC_HELICOPTER_GO_TO_AGROPROM_INFO silently (the helicopter flight is gone)
  2. esc_smart_terrain_1_trader_sidorovich_go_to_fox  becomes the ORIGINAL SoC escape_trader_jobs "military case" talk, available right after the flash drive
  3. esc_smart_terrain_7_military_kuznetsov_*         the bridge pass costs 500 rubles (original SoC esc_bridge_soldiers_start), not 5 bottles of vodka
Dialog ids and flags are kept (saves, PDA archive, other patches). Run patches\\quest_dialogs\\gen_quest_dialogs.py afterwards."""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(os.path.dirname(here), 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l01_escape.xml')
data = open(path, 'rb').read()
NL = b'\r\n'

PASS = 'ESC_START_5_BOTTLES_OF_VODKA_FOR_KUZNETSOV_QUEST_TASK_INFO'       # the pass flag, name kept (zone restrictor, bridge logic)
JOB_DONE = 'ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO'
FLESH = 'ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO'
HELI = 'ESC_HELICOPTER_GO_TO_AGROPROM_INFO'


def phrase(pid, act, text, extra=(), nxt=()):
    s = ['            <phrase id="%s">' % pid, '                <action>%s</action>' % act, '                <text>%s</text>' % text]
    s += ['                ' + e for e in extra]
    s += ['                <next>%s</next>' % n for n in nxt]
    s.append('            </phrase>')
    return s


# ---- 2. Sidorovich: SoC military case (SoC phrases 0, 6, 61, 611, 6111, 61111, 611111, 6111111, 61111111, 611111111)
job = ['    <dialog id="esc_smart_terrain_1_trader_sidorovich_go_to_fox">',
       '        <has_flag>%s</has_flag>' % FLESH,
       '        <dont_has_flag>%s</dont_has_flag>' % JOB_DONE,
       '        <phrase_list>']
for i in range(10):
    extra = []
    if i == 7:
        extra = ['<give_flag>%s</give_flag>' % JOB_DONE]          # SoC gives agroprom_military_case here: a cut-off talk cannot block the chain
    if i == 9:
        extra = ['<give_flag>%s</give_flag>' % JOB_DONE, '<action>dialogs.break_dialog</action>']
    job += phrase(i, 'coop_soc_cordon.say_job_%d' % i, 'coop_soc_job_%d' % i, extra, [i + 1] if i < 9 else [])
job += ['        </phrase_list>', '    </dialog>']

# ---- 3. Kuznetsov
start = ['    <dialog id="esc_smart_terrain_7_military_kuznetsov_start_dialog">',
         '        <phrase_list>',
         '            <phrase id="0">', '                <text />', '                <next>10</next>', '                <next>20</next>', '            </phrase>',
         '            <!-- original SoC esc_bridge_soldiers_start: 11 off limits, 21 keep moving once the pass is paid -->',
         '            <phrase id="10">', '                <text />', '                <dont_has_flag>%s</dont_has_flag>' % PASS, '                <next>11</next>', '            </phrase>',
         '            <phrase id="11">', '                <action>coop_soc_cordon.say_bridge_11</action>', '                <text>coop_soc_bridge_11</text>', '            </phrase>',
         '            <phrase id="20">', '                <text />', '                <has_flag>%s</has_flag>' % PASS, '                <next>21</next>', '            </phrase>',
         '            <phrase id="21">', '                <action>coop_soc_cordon.say_bridge_21</action>', '                <text>coop_soc_bridge_21</text>', '            </phrase>',
         '        </phrase_list>', '    </dialog>']

pay = ['    <dialog id="esc_smart_terrain_7_military_kuznetsov_go_to_fox_1">',
       '        <dont_has_flag>%s</dont_has_flag>' % PASS,
       '        <phrase_list>']
pay += phrase(0, 'coop_soc_cordon.say_bridge_12', 'coop_soc_bridge_12', [], [1])
pay += phrase(1, 'coop_soc_cordon.say_bridge_13', 'coop_soc_bridge_13', [], [2, 4])
# any player can pay; the pass flag is a shared story flag, so the whole group is let through (as the vodka was)
pay += phrase(2, 'coop_soc_cordon.say_bridge_14', 'coop_soc_bridge_14',
              ['<precondition>coop_soc_cordon.has_bridge_bribe</precondition>',
               '<action>coop_soc_cordon.give_bridge_bribe</action>',
               '<give_flag>%s</give_flag>' % PASS,
               '<give_flag>ESC_SMART_TERRAIN_7_MILITARY_KUZNETSOV_GO_TO_FOX_1_STOP_DIALOG_INFO</give_flag>',
               '<give_flag>ESC_SMART_TERRAIN_7_MILITARY_KUZNETSOV_GO_TO_FOX_2_STOP_DIALOG_INFO</give_flag>'], [3])
pay += phrase(3, 'coop_soc_cordon.say_bridge_15', 'coop_soc_bridge_15', ['<action>dialogs.break_dialog</action>'], [])
pay += phrase(4, 'coop_soc_cordon.say_bridge_24', 'coop_soc_bridge_24', [], [5])
pay += phrase(5, 'coop_soc_cordon.say_bridge_25', 'coop_soc_bridge_25', ['<action>dialogs.break_dialog</action>'], [])
pay += ['        </phrase_list>', '    </dialog>']


def block(did):
    return re.compile(rb'[ \t]*<dialog id="%s"[^>]*>.*?</dialog>[ \t]*(?:\r?\n)?' % did.encode(), re.S)


def replace(data, did, lines):
    m = block(did).search(data)
    if m is None:
        if not lines:
            return data                 # already removed
        sys.exit('dialog %s not found' % did)
    new = NL.join(l.encode('cp1251') for l in lines) + NL if lines else b''
    return data[:m.start()] + new + data[m.end():]


data = replace(data, 'esc_smart_terrain_1_trader_sidorovich_go_to_fox', job)
data = replace(data, 'esc_smart_terrain_7_military_kuznetsov_start_dialog', start)
data = replace(data, 'esc_smart_terrain_7_military_kuznetsov_go_to_fox_1', pay)
data = replace(data, 'esc_smart_terrain_7_military_kuznetsov_go_to_fox_2', [])

# ---- 1. flash drive hand-in: the helicopter flag silently (phrase 2, next to the flag the hand-in already gives)
m = block('esc_smart_terrain_1_trader_sidorovich_flesh').search(data)
blk = m.group(0)
if HELI.encode() not in blk:
    anchor = re.compile(rb'(<phrase id="2">.*?<give_flag>%s</give_flag>[ \t]*\r?\n)' % FLESH.encode(), re.S)
    assert anchor.search(blk), 'flesh phrase 2 anchor'
    blk2 = anchor.sub(lambda mm: mm.group(1) + b'                <give_flag>' + HELI.encode() + b'</give_flag>' + NL, blk, count=1)
    data = data[:m.start()] + blk2 + data[m.end():]

open(path, 'wb').write(data)
print('ok', len(data))
