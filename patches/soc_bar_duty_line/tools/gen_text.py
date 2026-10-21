"""Make configs\\text\\eng|rus\\st_coop_soc_duty.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings (+ the few lines of duty_model.AUTH).

  python gen_text.py <steam soc extract dir> <port rus st_soc_strings.xml>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings of the CoP-port add-on (utf-8 or cp1251)
Every id of the output is a SoC string under a coop_soc_duty_* name (or an AUTH line). Model: duty_model.py."""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import duty_model as M

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


def fix(s):
    return s.replace('basi?ally', 'basically').replace("alight?", "alright?")


ROWS = []     # (new id, eng, rus)


def soc(new, old):
    for lang, src in (('eng', ENG), ('rus', RUS)):
        if old not in src:
            sys.exit('missing SoC string %s (%s)' % (old, lang))
    ROWS.append((new, fix(ENG[old]), fix(RUS[old])))


def auth(new, key):
    e, r = M.AUTH[key]
    ROWS.append((new, e, r))


for key, d in M.DIALOGS.items():
    for pid, spk, nxt, pre, flags, acts in d['phrases']:
        if spk == M.H:
            continue
        new = 'coop_soc_duty_%s_%s' % (key, pid)
        if (key, pid) in M.AUTH_PHRASE:
            auth(new, M.AUTH_PHRASE[(key, pid)])
        else:
            soc(new, M.SRC_ALIAS.get((key, pid), d['src'] + pid))

for new, old in M.CHAR_STRINGS.items():
    soc(new, old)

for t in M.TASKS:
    base = 'coop_soc_duty_' + t['id']
    kind, k = t['title']
    (soc if kind == 'soc' else auth)(base + '_name', k)
    for i, (cond, (kind, k), tgt) in enumerate(t['steps']):
        (soc if kind == 'soc' else auth)('%s_s%d' % (base, i), k)

for key, new in (('item_lucky_name', 'coop_soc_duty_lucky_pda_name'), ('item_lucky_desc', 'coop_soc_duty_lucky_pda_desc'),
                 ('item_tyran_name', 'coop_soc_duty_tyran_pda_name'), ('item_tyran_desc', 'coop_soc_duty_tyran_pda_desc')):
    auth(new, key)

for li, lang in enumerate(('eng', 'rus')):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for row in ROWS:
        lines.append('\t<string id="%s"><text>%s</text></string>' % (row[0], row[1 + li]))
    lines.append('</string_table>')
    txt = '\r\n'.join(lines) + '\r\n'
    assert chr(0x2014) not in txt, 'em dash'
    bad = [c for c in txt if ord(c) > 127 and lang == 'eng']
    if bad:
        print('WARN non-ascii in eng:', ''.join(sorted(set(bad))))
    d = os.path.join(out, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'st_coop_soc_duty.xml'), 'wb') as f:
        f.write(txt.encode('cp1251', errors='replace'))
    print(lang, len(ROWS), 'strings')
