"""Make configs\\text\\eng|rus\\st_coop_soc_doctor.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Output goes to patches\\soc_doctor_chain\\gamedata\\configs\\text. Nothing is invented: every string is a SoC string (several ids joined by two `\\n`
escapes where a task shows the objective and then the briefing, like soc_aes_quests and soc_yan_x16_quests).
"""
import os
import re
import sys

steam, rus_file = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), 'gamedata', 'configs', 'text')


def load(raw):
    try:
        t = raw.decode('utf-8')
    except UnicodeDecodeError:
        t = raw.decode('cp1251', errors='replace')
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'<string id="([^"]*)">\s*<text>(.*?)</text>', t, re.S)}


ENG = {}
for dp, dn, fn in os.walk(os.path.join(steam, 'config', 'text', 'eng')):
    for f in fn:
        if f.endswith('.xml'):
            ENG.update(load(open(os.path.join(dp, f), 'rb').read()))
RUS = load(open(rus_file, 'rb').read())

# new id -> [SoC string ids]
JOIN = {
    # the Guide (SoC esc_provodnik_start, branch 12 to 16; the greeting 11 is the mod's own Guide greeting)
    'coop_soc_doc_g_0': ['esc_provodnik_start_12'],
    'coop_soc_doc_g_1': ['esc_provodnik_start_13'],
    'coop_soc_doc_g_2': ['esc_provodnik_start_14'],
    'coop_soc_doc_g_3': ['esc_provodnik_start_15'],
    'coop_soc_doc_g_4': ['esc_provodnik_start_16'],
    # the Doctor: greeting (SoC cit_doctor_hello_dialog) and the talk (SoC cit_doctor_main_dialog, without the two lines about Dead City)
    'coop_soc_doc_d_h11': ['cit_doctor_hello_dialog_11'],
    'coop_soc_doc_d_h21': ['cit_doctor_hello_dialog_21'],
    'coop_soc_doc_d_0': ['cit_doctor_main_dialog_0'],
    'coop_soc_doc_d_1': ['cit_doctor_main_dialog_1'],
    'coop_soc_doc_d_11': ['cit_doctor_main_dialog_11'],
    'coop_soc_doc_d_2': ['cit_doctor_main_dialog_2'],
    'coop_soc_doc_d_21': ['cit_doctor_main_dialog_21'],
    'coop_soc_doc_d_3': ['cit_doctor_main_dialog_3'],
    'coop_soc_doc_d_31': ['cit_doctor_main_dialog_31'],
    'coop_soc_doc_d_4': ['cit_doctor_main_dialog_4'],
    # character
    'coop_soc_doc_name': ['cit_doctor_name'],
    'coop_soc_doc_bio': ['cit_doctor_bio'],
    # SoC doctor_meet: "Meet with Doctor", objective 2 + the Doctor's note; SoC cit_doctor_task: "Secret stash at Pripyat", objective 0 + the Doctor's briefing
    'coop_soc_doc_meet_name': ['meet_with_doctor'],
    'coop_soc_doc_meet_descr': ['meet_with_doctor_2', 'doctor_meet_quest_text'],
    'coop_soc_doc_stash_name': ['cit_doctor_task'],
    'coop_soc_doc_stash_descr': ['cit_doctor_task_0', 'cit_doctor_task_0_art'],
    # diary / PDA lines shown once: the Guide's PDA note (SoC article esc_provodnik_pda) and "Meeting with the Doctor" (SoC cit_doctor_meet_conclusion_art)
    'coop_soc_doc_pda_name': ['doctor_meet'],
    'coop_soc_doc_pda_text': ['doctor_meet_text'],
    'coop_soc_doc_concl_name': ['cit_doctor_meet_conclusion'],
    'coop_soc_doc_concl_text': ['cit_doctor_meet_conclusion_txt'],
}

for lang, src in (('eng', ENG), ('rus', RUS)):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for new, olds in JOIN.items():
        for o in olds:
            if o not in src:
                sys.exit('missing SoC string %s (%s)' % (o, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, '\\n\\n'.join(src[o] for o in olds)))
    lines.append('</string_table>')
    txt = '\r\n'.join(lines) + '\r\n'
    assert chr(0x2014) not in txt, 'em dash'
    d = os.path.join(out, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'st_coop_soc_doctor.xml'), 'wb') as f:
        f.write(txt.encode('cp1251'))
    print(lang, len(JOIN), 'strings')
