"""Make configs\\text\\eng|rus\\st_coop_soc_yan_semenov.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>   xdb_soc.py extraction with config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1252 bytes)
<port rus st_soc_strings.xml>  Russian SoC strings of the CoP-port add-on (cp1251)
Output: patches\\soc_yan_semenov\\gamedata\\configs\\text\\{eng,rus}\\st_coop_soc_yan_semenov.xml. Every id is a SoC string under a coop_soc_yan_sem_* name.
  coop_soc_yan_sem_s_<id>   Sakharov dialog yantar_general_ucheniy_talk_start_<id>   (branch 21113: the offer when the professor is dead,
                            branch 5: Semenov died)
  coop_soc_yan_sem_m_<id>   Semenov dialog yantar_help_scientist_<id>
  coop_soc_yan_sem_w_<id>   wounded scientist dialog yantar_wounded_scientist_<id>
and the name, bio, task and tip strings of JOIN below.
"""
import os
import re
import sys

steam, rus_file = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), 'gamedata', 'configs', 'text')

S_IDS = ['21113', '211131', '211132',
         '51', '511', '5111', '51111', '511111', '5111111', '511111111', '51112', '51113', '51114']
M_IDS = ['61', '51', '511', '512', '513', '514', '515', '101', '71']
W_IDS = ['11', '111', '211', '31']

MAP = {}
for i in S_IDS:
    MAP['coop_soc_yan_sem_s_' + i] = 'yantar_general_ucheniy_talk_start_' + i
for i in M_IDS:
    MAP['coop_soc_yan_sem_m_' + i] = 'yantar_help_scientist_' + i
for i in W_IDS:
    MAP['coop_soc_yan_sem_w_' + i] = 'yantar_wounded_scientist_' + i
MAP.update({
    'coop_soc_yan_sem_name': 'yan_semenov_name',
    'coop_soc_yan_sem_bio': 'yan_semenov_bio',
    'coop_soc_yan_sem_return_name': 'yan_scientist_return_task',
    'coop_soc_yan_sem_tip_1': 'general_ecolog_tip_1',
    'coop_soc_yan_sem_tip_2': 'general_ecolog_tip_2',
})

JOIN = {
    # yan_find_scientist_semenov objective 1 + the Sakharov briefing; objective 2
    'coop_soc_yan_sem_talk_descr': ['yan_talk_to_semenov', 'descr_yan_find_scientist_semenov'],
    'coop_soc_yan_sem_escort_descr': ['yan_psi_zone_find_semenov'],
    # yan_scientist_return_task objective 1 + its briefing
    'coop_soc_yan_sem_return_descr': ['yan_scientist_return_task', 'descr_yan_scientist_return_task'],
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
    with open(os.path.join(d, 'st_coop_soc_yan_semenov.xml'), 'wb') as f:
        f.write(txt.encode('cp1251', errors='replace'))
    print(lang, len(MAP) + len(JOIN), 'strings')
