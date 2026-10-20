#!/usr/bin/env python3
"""Builds gamedata/scripts/stash_markers_data.script and configs/text/{rus,eng}/stash_markers.xml.
Inputs: SoC treasure_manager.ltx + rus strings (refs dir), SoC alife dumps (stash_loot refs), English translation json,
the Shadow of COOP level.spawn files (boxes matched to the SoC stash boxes by level + position <= 0.3 m, as stash_loot does).
Run with python -I.  Paths default to the owner's folders."""
import os, re, sys, json, math, struct
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import xdb
DL = os.path.join(os.path.expanduser('~'), 'Downloads')
REF = os.path.join(DL, 'SoC_COOP_features', 'stash_markers', 'refs')
ALIFE = os.path.join(DL, 'SoC_COOP_stashes', 'refs', 'soc1006')
ADDON = os.path.join(DL, 'Shadow of COOP 8.0', 'addon_unpacked')
OUT = os.path.join(HERE, '..', 'gamedata')
LV = [('l01_escape','coop_l01_escape'),('l02_garbage','coop_l02_garbage'),('l03_agroprom','coop_l03_agroprom'),('l03u_agr_underground','coop_l03_agroprom_underground'),('l04_darkvalley','coop_l04_darkvalley'),('l04u_labx18','coop_l04_x18'),('l05_bar','coop_l05_bar'),('l06_rostok','coop_l06_rostok'),('l07_military','coop_l07_military'),('l08_yantar','coop_l08_yantar'),('l10_radar','coop_l09_radar'),('l10u_bunker','coop_l09_x10'),('l11_pripyat','coop_l10_pripyat'),('l12_stancia','coop_l11_stancia_1'),('l12_stancia_2','coop_l11_stancia_2'),('l12u_control_monolith','coop_l11_control_monolith'),('l12u_sarcofag','coop_l11_sarcofag')]


def soc_boxes():
    res = {}
    for s, m in LV:
        t = open(os.path.join(ALIFE, 'alife_%s.ltx' % s), 'rb').read().decode('latin1').replace('\r', '')
        for b in re.split(r'\n\n(?=\[)', t):
            sec = re.search(r'^section_name\s*=\s*(\S+)', b, re.M)
            if not sec or sec.group(1) != 'inventory_box':
                continue
            sid = re.search(r'^story_id\s*=\s*(\S+)', b, re.M)
            if not sid or not sid.group(1).isdigit():
                continue
            pos = tuple(float(x) for x in re.search(r'^position\s*=\s*(.+)$', b, re.M).group(1).replace(' ', '').split(','))
            res[int(sid.group(1))] = (m, pos)
    return res


def mod_boxes(level):
    out = []
    for dbn in ('gamedata.db0', 'gamedata.db1'):
        p = os.path.join(ADDON, dbn)
        f = open(p, 'rb')
        idx = xdb.index(f, 0, os.path.getsize(p))
        for name, rs, cs, ptr in idx:
            if name == 'levels\\%s\\level.spawn' % level:
                f.seek(ptr)
                d = f.read(cs)
                if rs != cs:
                    d = xdb.lzo1x(d, rs)
                o = 0
                while o + 8 <= len(d):
                    _, s = struct.unpack_from('<II', d, o)
                    o += 8
                    c = d[o:o + s]
                    o += s
                    m = re.match(rb'\x01\x00([^\x00]*)\x00([^\x00]*)\x00', c)
                    if m and m.group(1) == b'inventory_box':
                        out.append((m.group(2).decode('latin1'), struct.unpack_from('<3f', c, m.end() + 2)))
                return out
    return []


def parse_ltx(path):
    t = open(path, 'rb').read().decode('latin1').replace('\r', '')
    secs = {}
    cur = None
    order = []
    for ln in t.split('\n'):
        ln = ln.split(';')[0].strip()
        if not ln:
            continue
        m = re.match(r'^\[(.+)\]$', ln)
        if m:
            cur = m.group(1)
            secs[cur] = {}
            continue
        if cur and '=' in ln:
            k, v = ln.split('=', 1)
            secs[cur][k.strip()] = v.strip()
        elif cur == 'list':
            order.append(ln)
    return secs, order


def parse_cond(s):
    out = []
    depth = 0
    part = ''
    parts = []
    for ch in s:
        if ch == '{':
            depth += 1
        if ch == '}':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(part)
            part = ''
        else:
            part += ch
    parts.append(part)
    for p in parts:
        m = re.match(r'^\s*(?:\{(.*?)\})?\s*(\S*)\s*$', p)
        if not m:
            continue
        e = {'p': float(m.group(2)) if m.group(2) else 0}
        for tk in (m.group(1) or '').split():
            r = re.match(r'^=npc_rank\((\w+)\)$', tk)
            if r:
                e['rank'] = r.group(1)
                continue
            r = re.match(r'^=actor_on_level\((\w+)\)$', tk)
            if r:
                e['lvl'] = r.group(1)
                continue
            r = re.match(r'^=npc_profile\((\w*)\)$', tk)
            if r:
                e['prof'] = r.group(1)
                continue
            if tk[0] == '+':
                e.setdefault('need', []).append(tk[1:])
            elif tk[0] == '-':
                e.setdefault('avoid', []).append(tk[1:])
        out.append(e)
    return out


def strings(path):
    t = open(path, 'rb').read().decode('cp1251')
    return dict(re.findall(r'<string id="([^"]+)">\s*<text>(.*?)</text>', t, re.S))


def q(x):
    return '"%s"' % x


def main():
    secs, order = parse_ltx(os.path.join(REF, 'soc_treasure_manager.ltx'))
    order = [o for o in order if o in secs]
    rus = strings(os.path.join(REF, 'soc_stable_treasure_manager_rus.xml'))
    eng = json.load(open(os.path.join(REF, 'stash_en.json'), encoding='utf-8'))
    sb = soc_boxes()
    mb = {m: mod_boxes(m) for _, m in LV}
    rows = []
    miss = []
    for tid in order:
        s = secs[tid]
        tgt = int(s['target'])
        if tgt not in sb:
            miss.append((tid, 'no soc box'))
            continue
        lvl, pos = sb[tgt]
        best = min(((math.dist(pos, p), n) for n, p in mb[lvl]), default=(99, None))
        if best[0] > 0.3:
            miss.append((tid, 'no mod box %.2f' % best[0]))
            continue
        nm, ds = s['name'], s.get('description')
        if nm not in rus or ds not in rus or nm not in eng or ds not in eng:
            miss.append((tid, 'no text'))
            continue
        comm = [c.strip() for c in s.get('community', 'stalker, bandit, dolg, freedom').split(',')]
        rows.append(dict(id=tid, lvl=lvl, box=best[1], comm=comm, cond=parse_cond(s.get('condlist', '')), nm=nm, ds=ds))
    seen = {}
    for r in rows:
        if r['box'] in seen:
            miss.append((r['id'], 'duplicate box with ' + seen[r['box']]))
        seen[r['box']] = r['id']
    L = ['-- GENERATED by tools/gen_stash_markers.py, do not edit. SoC treasure_manager.ltx stashes mapped to Shadow of COOP inventory boxes.',
         'levels = {']
    for s, m in LV:
        L.append('\t[%s] = %s,' % (q(m), q(s)))
    L.append('}')
    L.append('stashes = {')
    for r in rows:
        c = []
        for e in r['cond']:
            f = ['p=%g' % e['p']]
            for k in ('rank', 'lvl', 'prof'):
                if k in e:
                    f.append('%s=%s' % (k, q(e[k])))
            for k in ('need', 'avoid'):
                if k in e:
                    f.append('%s={%s}' % (k, ','.join(q(x) for x in e[k])))
            c.append('{' + ','.join(f) + '}')
        L.append('\t{id=%s,lvl=%s,box=%s,comm={%s},cond={%s}},' % (q(r['id']), q(r['lvl']), q(r['box']),
                 ','.join('%s=true' % x for x in r['comm']), ','.join(c)))
    L.append('}')
    open(os.path.join(OUT, 'scripts', 'stash_markers_data.script'), 'wb').write(('\r\n'.join(L) + '\r\n').encode('ascii'))

    def xml(lang):
        o = ['<?xml version="1.0" encoding="windows-1251" ?>', '<string_table>']
        for r in rows:
            if lang == 'rus':
                n, d = rus[r['nm']], rus[r['ds']]
            else:
                n, d = eng[r['nm']], eng[r['ds']]
            n = n.replace('\n', ' ')
            d = d.replace('\n', ' ')
            o.append('\t<string id="stash_hint_%s">\n\t\t<text>%%c[255,238,155,23]%s\\n%%c[default]%s</text>\n\t</string>' % (r['id'], n, d))
        o.append('</string_table>')
        return ('\r\n'.join(o) + '\r\n').encode('cp1251', 'replace')
    for lang in ('rus', 'eng'):
        open(os.path.join(OUT, 'configs', 'text', lang, 'stash_markers.xml'), 'wb').write(xml(lang))
    per = {}
    for r in rows:
        per[r['lvl']] = per.get(r['lvl'], 0) + 1
    print('stashes', len(rows), 'of', len(order), per)
    print('missed', miss)


main()
