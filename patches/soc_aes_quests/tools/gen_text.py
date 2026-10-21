"""Make configs\\text\\eng|rus\\st_coop_soc_aes.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Output goes to patches\\soc_aes_quests\\gamedata\\configs\\text. Every new task id of this patch gets a title / description made of SoC strings
(two `\\n` escapes between the objective and the briefing, like soc_task_texts and soc_dv_x18_quests).
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

# new id -> [SoC string ids]; more than one id = objective, then the briefing article, joined by two \n escapes
JOIN = {
    # SoC cit_doctor_task (tasks_deadcity.xml): "Secret stash at Pripyat", objectives 1..3 (objective 0 has no text), briefing = the Doctor's article
    'st_pri_soc_stash_name': ['cit_doctor_task'],
    'st_pri_soc_stash_1_descr': ['cit_doctor_task_1', 'cit_doctor_task_0_art'],
    'st_pri_soc_stash_2_descr': ['cit_doctor_task_2'],
    'st_pri_soc_stash_3_descr': ['cit_doctor_task_3'],
    # SoC sar_monolith (tasks_sarcofag.xml): objective 0 is the existing sar_start_get_to_the_monolith_quest_task (soc_task_texts), 1 and 2 are new
    'st_sar_soc_wish_name': ['sar_monolith'],
    'st_sar_soc_sneak_in_descr': ['sar_monolith_1'],
    'st_sar_soc_find_wish_descr': ['sar_monolith_2'],
    # SoC sar_secret_lab: objective 2 is the existing sar_start_open_the_door_to_monolith_management_quest_task (soc_task_texts)
    'st_sar_soc_lab_name': ['sar_secret_lab'],
    'st_sar_soc_lab_1_descr': ['sar_secret_lab_0', 'sar_secret_lab_text'],
    'st_sar_soc_lab_2_descr': ['sar_secret_lab_1'],
    'st_sar_soc_lab_4_descr': ['sar_secret_lab_3'],
    # map spot on the stash decoder and the diary line shown when it is picked up (SoC article pri_decoder_docs_conclusion)
    'coop_soc_aes_stash_hint': ['cit_doctor_task_2'],
    'coop_soc_aes_stash_news_name': ['pri_decoder_docs_conclusion'],
    'coop_soc_aes_stash_news_text': ['pri_decoder_docs_conclusion_txt'],
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
    with open(os.path.join(d, 'st_coop_soc_aes.xml'), 'wb') as f:
        f.write(txt.encode('cp1251'))
    print(lang, len(JOIN), 'strings')
