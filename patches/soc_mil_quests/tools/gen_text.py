"""Make configs\\text\\eng|rus\\st_coop_soc_mil.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Every id of the output is a SoC string under a coop_soc_mil_* / st_mil_soc_* name. Model: mil_model.py."""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import mil_model as M

steam, rus_file = sys.argv[1], sys.argv[2]
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

MAP = {}      # new id -> SoC id
for key, d in M.DIALOGS.items():
    for pid, spk, nxt, pre, flags, acts in d['phrases']:
        if spk == M.H or (key == 'mx' and pid == '31'):
            continue
        MAP['coop_soc_mil_%s_%s' % (key, pid)] = d['src'] + pid

JOIN = {}     # new id -> [SoC ids], joined by two \n escapes
for t in M.NEW_TASKS:
    base = 'st_' + t['id'][:-5]          # st_mil_soc_return_lukash
    JOIN[base + '_name'] = [t['name']]
    JOIN[base + '_descr'] = [t['descr']]


def fix(s):
    return s.replace('basi?ally', 'basically').replace("alight?", "alright?")


for lang, src in (('eng', ENG), ('rus', RUS)):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for new, old in MAP.items():
        if old not in src:
            sys.exit('missing SoC string %s (%s)' % (old, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, fix(src[old])))
    for new, olds in JOIN.items():
        for o in olds:
            if o not in src:
                sys.exit('missing SoC string %s (%s)' % (o, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, '\\n\\n'.join(fix(src[o]) for o in olds)))
    lines.append('</string_table>')
    txt = '\r\n'.join(lines) + '\r\n'
    assert chr(0x2014) not in txt, 'em dash'
    bad = [c for c in txt if ord(c) > 127 and lang == 'eng']
    if bad:
        print('WARN non-ascii in eng:', ''.join(sorted(set(bad))))
    d = os.path.join(out, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'st_coop_soc_mil.xml'), 'wb') as f:
        f.write(txt.encode('cp1251', errors='replace'))
    print(lang, len(MAP) + len(JOIN), 'strings')
