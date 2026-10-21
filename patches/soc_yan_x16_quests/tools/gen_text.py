"""Make configs\\text\\eng|rus\\st_coop_soc_yan.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>   xdb_soc.py extraction with config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1252 bytes)
<port rus st_soc_strings.xml>  Russian SoC strings of the CoP-port add-on (cp1251)
Output: patches\\soc_yan_x16_quests\\gamedata\\configs\\text\\{eng,rus}\\st_coop_soc_yan.xml. Every id is a SoC string under a coop_soc_yan_* name.
  coop_soc_yan_s_<id>   Sakharov dialog yantar_general_ucheniy_talk_start_<id>
  coop_soc_yan_k_<id>   Kruglov dialog yantar_help_scientist_<id>
and the task / item strings of JOIN below (objective text, then the SoC briefing, joined by two \\n like phase 1 did).
"""
import os
import re
import sys

steam, rus_file = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), 'gamedata', 'configs', 'text')

S_IDS = ['11', '111', '211', '2111', '21111', '21112', '211121', '2111211', '21115', '211151',
         '101', '1011', '1012', '1013', '1014', '10141', '101411', '101412', '10143', '101431',
         '31', '311', '3111', '31111', '311111', '311112', '311113', '311114',
         '61', '71', '231', '2311']
K_IDS = ['11', '111', '1111', '11111', '111111', '1111111', '21', '41', '71', '101']

MAP = {}
for i in S_IDS:
    MAP['coop_soc_yan_s_' + i] = 'yantar_general_ucheniy_talk_start_' + i
for i in K_IDS:
    MAP['coop_soc_yan_k_' + i] = 'yantar_help_scientist_' + i

JOIN = {
    # yan_scientist_job
    'coop_soc_yan_job_name': ['yan_scientist_job'],
    'coop_soc_yan_job_descr': ['yan_scientist_job_text'],
    # yan_find_vasilyev_task objective 1 + the Sakharov briefing (objective 2 "Get inside the lab" is the phase 1 string)
    'coop_soc_yan_vasilyev_descr': ['yan_find_vasilyev', 'descr_yan_find_lab'],
    # yan_find_ghost_task
    'coop_soc_yan_ghost_name': ['yan_find_ghost_task'],
    'coop_soc_yan_ghost_1_descr': ['yan_find_labX16', 'descr_yan_find_ghost_task'],
    'coop_soc_yan_ghost_2_descr': ['yan_find_ghost'],
    # yan_kill_brain_task_2 objective 1 + its briefing
    'coop_soc_yan_tunnel_descr': ['yan_secret_tonnel', 'descr_yan_kill_brain_2'],
    # yan_provodnik_task
    'coop_soc_yan_guide_name': ['yan_provodnik_task'],
    'coop_soc_yan_guide_descr': ['yan_provodnik_about_doctor', 'descr_yan_provodnik_task'],
    # Vasiliev's PDA (SoC article yan_vasilyev_info) and its tip
    'coop_soc_yan_vasilyev_pda_name': ['yan_vasilyev_pda'],
    'coop_soc_yan_vasilyev_pda_descr': ['storyline_vasilyev_info'],
    'coop_soc_yan_vasilyev_tip': ['storyline_vasilyev_tip'],
}


def load(raw, enc):
    t = raw.decode(enc, errors='replace')
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'<string id="([^"]*)">\s*<text>(.*?)</text>', t, re.S)}


ENG = {}
for dp, dn, fn in os.walk(os.path.join(steam, 'config', 'text', 'eng')):
    for f in fn:
        if f.endswith('.xml'):
            ENG.update(load(open(os.path.join(dp, f), 'rb').read(), 'cp1252'))
RUS = load(open(rus_file, 'rb').read(), 'cp1251')

ASCII = {chr(c): r for c, r in ((0x2019, "'"), (0x2018, "'"), (0x201c, '"'), (0x201d, '"'), (0x2026, '...'), (0x2013, '-'), (0x2014, '-'), (0xab, '"'), (0xbb, '"'))}


def clean(s, lang):
    for a, b in ASCII.items():
        s = s.replace(a, b)
    if lang == 'eng':
        s = s.encode('ascii', errors='replace').decode('ascii')
    s = s.replace('&', '&amp;') if re.search(r'&(?!amp;|lt;|gt;|quot;|apos;)', s) else s
    return s


for lang, src in (('eng', ENG), ('rus', RUS)):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for new, old in MAP.items():
        if old not in src:
            sys.exit('missing SoC string %s (%s)' % (old, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, clean(src[old], lang)))
    for new, olds in JOIN.items():
        for o in olds:
            if o not in src:
                sys.exit('missing SoC string %s (%s)' % (o, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, clean('\\n\\n'.join(src[o] for o in olds), lang)))
    lines.append('</string_table>')
    txt = '\r\n'.join(lines) + '\r\n'
    assert chr(0x2014) not in txt, 'em dash'
    d = os.path.join(out, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'st_coop_soc_yan.xml'), 'wb') as f:
        f.write(txt.encode('cp1251', errors='replace'))
    print(lang, len(MAP) + len(JOIN), 'strings')
