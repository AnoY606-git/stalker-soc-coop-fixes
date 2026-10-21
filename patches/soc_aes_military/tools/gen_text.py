"""Make configs\\text\\eng|rus\\st_coop_soc_aes_military.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Output goes to patches\\soc_aes_military\\gamedata\\configs\\text. Nothing is invented: every string is a SoC string (string_table_tasks_aes.xml,
stable_storyline_info_aes.xml). Descriptions are the objective text, then (two `\\n` escapes) the briefing article "Military action plan".
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
    # the task: SoC aes_military_task "Operation Monolith"; the objectives of tasks_aes.xml in the order the party meets them
    'st_aes_military_name': ['aes_military_task'],
    'st_aes_military_1_descr': ['aes_military_task_1', 'aes_soldier_info'],     # Capture the gate
    'st_aes_military_2_descr': ['aes_military_task_4', 'aes_soldier_info'],     # Destroy the Monolith 1 fortifications
    'st_aes_military_3_descr': ['aes_military_task_5', 'aes_soldier_info'],     # Destroy the Monolith 2 fortifications
    'st_aes_military_4_descr': ['aes_military_task_3', 'aes_soldier_info'],     # Break through to the sarcophagus
    # map spot hints (the SoC map_location_type hints of the objectives)
    'coop_soc_aesm_gate': ['aes_military_task_1'],
    'coop_soc_aesm_mono1': ['aes_military_task_4'],
    'coop_soc_aesm_mono2': ['aes_military_task_5'],
    'coop_soc_aesm_sarc': ['aes_military_task_3'],
    'coop_soc_aesm_g_sapsan': ['aes_military_task_6'],
    'coop_soc_aesm_g_korshun': ['aes_military_task_7'],
    'coop_soc_aesm_g_yastreb': ['aes_military_task_8'],
    'coop_soc_aesm_g_pustelga': ['aes_military_task_9'],
    'coop_soc_aesm_g_sokol': ['aes_military_task_10'],
    'coop_soc_aesm_g_grif': ['aes_military_task_11'],
    'coop_soc_aesm_g_sova': ['aes_military_task_12'],
    'coop_soc_aesm_g_lun': ['aes_military_task_13'],
    # the diary article that comes with the plan (SoC storyline_info_aes.xml: article "Situation")
    'coop_soc_aesm_news_name': ['aes_military_task_head'],
    'coop_soc_aesm_news_text': ['aes_soldier_info'],
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
    with open(os.path.join(d, 'st_coop_soc_aes_military.xml'), 'wb') as f:
        f.write(txt.encode('cp1251'))
    print(lang, len(JOIN), 'strings')
