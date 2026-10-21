"""Make configs\\text\\eng|rus\\st_coop_soc_dv.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Output goes to patches\\soc_dv_x18_quests\\gamedata\\configs\\text. Every id is a SoC string under a coop_soc_* / st_soc_* name.
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

# Barkeep dialog (SoC bar_bar_barmen_start): phrase ids of the part Agroprom documents -> X18 job -> X18 documents -> X16 job
BARMAN = ['2', '21', '211', '2111', '22', '221', '2211', '151', '1511', '15111', '15112', '15113', '15114', '15115',
          '171', '172', '173', '1731', '1721', '17211', '17212', '17213', '17214', '172131', '172141', '181']

MAP = {}
for i in BARMAN:
    MAP['coop_soc_barman_' + i] = 'bar_bar_barmen_start_' + i

# tasks: (new id, [SoC ids joined by two \n escapes])
JOIN = {
    'st_soc_darklab_name': ['bar_darklab_documents'],
    'st_soc_darklab_1_descr': ['bar_darklab_documents_4', 'bar_darklab_documents_txt'],   # first step also carries the SoC briefing
    'st_soc_darklab_2_descr': ['bar_darklab_documents_1'],
    'st_soc_darklab_3_descr': ['bar_darklab_documents_2'],
    'st_soc_darklab_4_descr': ['bar_darklab_documents_3'],
    'st_soc_prisoner_name': ['val_prisoner_help'],
    'st_soc_prisoner_descr': ['val_prisoner_help_main', 'val_prisoner_help_art_txt'],
    'st_soc_codedoor_1_open_name': ['dar_codedoor_1'],
    'st_soc_codedoor_1_open_descr': ['dar_codedoor_1_2'],
    'st_soc_codedoor_2_open_name': ['dar_codedoor_2'],
    'st_soc_codedoor_2_open_descr': ['dar_codedoor_2_2'],
}

for lang, src in (('eng', ENG), ('rus', RUS)):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for new, old in MAP.items():
        if old not in src:
            sys.exit('missing SoC string %s (%s)' % (old, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, src[old]))
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
    with open(os.path.join(d, 'st_coop_soc_dv.xml'), 'wb') as f:
        f.write(txt.encode('cp1251'))
    print(lang, len(MAP) + len(JOIN), 'strings')
