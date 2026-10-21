"""Makes configs\\misc\\tm_coop_l11_stancia_1.ltx of patch soc_aes_military: the mod's own file, byte for byte, plus the SoC task "Operation Monolith".

  python make_tm.py <mod gamedata.db0 folder> <patch gamedata folder>

Idempotent (the section is replaced when it is already there). No other patch ships this file; task_manager.ltx (repeatable_quests) already includes it.
The SoC task has 13 objectives that all end with the info aes_found_sarcofag (tasks_aes.xml). The mod has ONE target per task, so the objectives the
party meets in a row are the steps of this one task (description and target follow the story flags set by coop_soc_aes_military.script); the markers of
the eight army groups and of the Monolith fortifications are map spots made by the script.
"""
import os
import re
import sys

mod, out = sys.argv[1], sys.argv[2]
NL = '\r\n'

SRC = os.path.join(mod, 'configs', 'misc', 'tm_coop_l11_stancia_1.ltx')
DST = os.path.join(out, 'configs', 'misc', 'tm_coop_l11_stancia_1.ltx')

GATE = 'SOC_AESM_GATE'
MONO1 = 'SOC_AESM_MONO1'
MONO2 = 'SOC_AESM_MONO2'
FOUND = 'SOC_AESM_FOUND'

SECTION = [
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    ';-- soc_aes_military: SoC aes_military_task "Operation Monolith" (tasks_aes.xml). Given by coop_soc_aes_military.script to EVERY player on CNPP-1 after',
    ';-- the military action plan was found; done at the sarcophagus (SoC infoportion aes_found_sarcofag). No reward (SoC pays nothing).',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    '[aes_military_task]',
    'icon 									= ui_inGame2_aes_1_start_go_to_sarcofag_quest_task',
    'prior 									= 190',
    'storyline 								= true',
    'title 									= st_aes_military_name',
    'descr 									= {+%s} st_aes_military_4_descr, {+%s} st_aes_military_3_descr, {+%s} st_aes_military_2_descr, st_aes_military_1_descr' % (MONO2, MONO1, GATE),
    'target 									= aes_1_level_changer',
    'condlist_0 								= {+%s} complete' % FOUND,
]


def main():
    raw = open(SRC, 'rb').read()
    text = raw.decode('utf-8')
    m = re.search(r'(?ms)^;-+\r?\n;-- soc_aes_military:.*?(?=\Z)', text)
    if m:
        text = text[:m.start()]
    text = text.rstrip('\r\n') + NL + NL + NL.join(SECTION) + NL
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, 'wb').write(text.encode('utf-8'))
    print('wrote', DST, len(text))


main()
