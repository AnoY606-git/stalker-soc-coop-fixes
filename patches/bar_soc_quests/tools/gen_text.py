"""Make configs\\text\\eng|rus\\st_coop_soc_barros.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Output goes to patches\\bar_soc_quests\\gamedata\\configs\\text. Every id is a SoC string under a coop_soc_* name.
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

MAP = {}
# Barkeep dialog (SoC bar_bar_barmen_start): the X16 documents hand-in and the Brain Scorcher job (the earlier part is in patch soc_dv_x18_quests)
for i in ['121', '1211', '1212', '12121', '121211', '131', '1312', '13121', '1313', '1314', '1315', '1316', '132', '1321', '161', '162']:
    MAP['coop_soc_barman_' + i] = 'bar_bar_barmen_start_' + i
# hunter (SoC bar_bar_hunter_start / bar_bar_hunter_quest_start / bar_bar_hunter_quest_finish)
MAP['coop_soc_hunter_problem'] = 'bar_bar_hunter_start_11'
MAP['coop_soc_hunter_news'] = 'bar_bar_hunter_start_21'
MAP['coop_soc_hunter_thanks'] = 'bar_bar_hunter_start_31'
for i in ['0', '1', '11', '111', '1111', '12', '121', '1212']:
    MAP['coop_soc_hunter_q_' + i] = 'bar_bar_hunter_quest_start_' + i
for i in ['0', '1']:
    MAP['coop_soc_hunter_f_' + i] = 'bar_bar_hunter_quest_finish_' + i
# task steps without a text of their own in the mod (objective texts of the SoC tasks)
MAP['coop_soc_x16_look_descr'] = 'look_for_x16_lab'
MAP['coop_soc_x16_bring_descr'] = 'bring_x16_documents'
MAP['coop_soc_hunter_return_descr'] = 'bar_hunter_return_rifle'
MAP['coop_soc_kruglov_talk_descr'] = 'bar_resque_scientific_information_get_2'
MAP['coop_soc_kruglov_bring_descr'] = 'bar_resque_scientific_information_bring'

for lang, src in (('eng', ENG), ('rus', RUS)):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for new, old in MAP.items():
        if old not in src:
            sys.exit('missing SoC string %s (%s)' % (old, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, src[old]))
    lines.append('</string_table>')
    txt = '\r\n'.join(lines) + '\r\n'
    assert chr(0x2014) not in txt, 'em dash'
    d = os.path.join(out, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'st_coop_soc_barros.xml'), 'wb') as f:
        f.write(txt.encode('cp1251'))
    print(lang, len(MAP), 'strings')
