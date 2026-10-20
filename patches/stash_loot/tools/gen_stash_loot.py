#!/usr/bin/env python3
"""Builds gamedata/scripts/stash_loot_data.script (and prints a coverage report).

Inputs
  * original SoC 1.0006 spawn dumps (alife_<level>.ltx) and ph_box_*.ltx configs. They are fetched
    from github.com/Roman-n/XRay-1.0006 (a plain copy of the 1.0006 gamedata) into --refs when missing.
  * the Shadow of COOP level.spawn files (read from the add-on .db with tools/xdb.py).
  * the mod's config tree (every [section] name), to check that every dropped item exists.

Why a table at all: the add-on spawn lost most [drop_box] custom_data and renamed the box objects, so
boxes are matched to the original SoC boxes by level + position (<= 0.3 m) and keyed by the mod's own
object name. Rebuild with:  python gen_stash_loot.py            (defaults point at the owner's folders)
"""
import argparse, glob, math, os, re, struct, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import xdb  # noqa: E402

RAW = 'https://raw.githubusercontent.com/Roman-n/XRay-1.0006/master/gamedata/'
# SoC level -> Shadow of COOP level (l08u_brainlab does not exist in the add-on)
LEVELS = [
    ('l01_escape', 'coop_l01_escape'), ('l02_garbage', 'coop_l02_garbage'),
    ('l03_agroprom', 'coop_l03_agroprom'), ('l03u_agr_underground', 'coop_l03_agroprom_underground'),
    ('l04_darkvalley', 'coop_l04_darkvalley'), ('l04u_labx18', 'coop_l04_x18'),
    ('l05_bar', 'coop_l05_bar'), ('l06_rostok', 'coop_l06_rostok'),
    ('l07_military', 'coop_l07_military'), ('l08_yantar', 'coop_l08_yantar'),
    ('l10_radar', 'coop_l09_radar'), ('l10u_bunker', 'coop_l09_x10'),
    ('l11_pripyat', 'coop_l10_pripyat'), ('l12_stancia', 'coop_l11_stancia_1'),
    ('l12_stancia_2', 'coop_l11_stancia_2'), ('l12u_control_monolith', 'coop_l11_control_monolith'),
    ('l12u_sarcofag', 'coop_l11_sarcofag'),
]
SOC_LEVEL_SECTION = {'l06_rostok': 'l06_Rostok'}   # the only level section with different case
MATCH_M = 0.3


def fetch(refs, rel, name):
    p = os.path.join(refs, name)
    if not os.path.exists(p):
        os.makedirs(refs, exist_ok=True)
        print('fetch', rel)
        urllib.request.urlretrieve(RAW + rel, p)
    return p


# ------------------------------------------------------------------ SoC spawn dump
def parse_soc_ltx(path):
    txt = open(path, 'rb').read().decode('latin1').replace('\r', '')
    out = []
    for b in re.split(r'\n\n(?=\[)', txt):
        m = re.search(r'^section_name\s*=\s*(\S+)', b, re.M)
        if not m or m.group(1) != 'physic_destroyable_object':
            continue
        n = re.search(r'^name\s*=\s*(.*)$', b, re.M).group(1).strip()
        p = re.search(r'^position\s*=\s*(.+)$', b, re.M).group(1).replace(' ', '').split(',')
        cd = re.search(r'^custom_data\s*=\s*<<END\n(.*?)\nEND', b, re.M | re.S)
        out.append(dict(name=n, pos=tuple(float(x) for x in p), cd=cd.group(1) if cd else ''))
    return out


def parse_drop_box(cd):
    """-> ('c', community) | ('i', [section, count, ...]) | None"""
    m = re.search(r'\[drop_box\](.*?)(?=\n\[|\Z)', cd, re.S)
    if not m:
        return None
    body = m.group(1)
    it = re.search(r'^\s*items\s*=\s*(.*)$', body, re.M)
    if it:  # same tokenizer as xr_box.parse_names / r_items
        t = re.findall(r'[\w\-.\\]+', it.group(1))
        out, k = [], 0
        while k < len(t):
            sec, cnt = t[k], 1
            if k + 1 < len(t) and re.fullmatch(r'\d+', t[k + 1]):
                cnt = int(t[k + 1]); k += 2
            else:
                k += 1
            out += [sec, cnt]
        return ('i', out)
    c = re.search(r'^\s*community\s*=\s*(\S+)', body, re.M)
    return ('c', c.group(1) if c else 'def_box')


# ------------------------------------------------------------------ SoC ph_box configs
def parse_ltx_sections(path, loaded=None):
    """Tiny ltx reader: sections with inheritance, #include. -> {name: {key: value}} (flattened)."""
    secs, order = {}, []

    def read(p):
        for line in open(p, 'rb').read().decode('latin1').replace('\r', '').split('\n'):
            line = line.split(';')[0].strip()
            if not line:
                continue
            m = re.match(r'#include\s+"(.+)"', line)
            if m:
                read(os.path.join(os.path.dirname(p), m.group(1)))
                continue
            m = re.match(r'\[([^\]]+)\]\s*(?::\s*(.+))?$', line)
            if m:
                cur = m.group(1)
                secs[cur] = dict(parents=[x.strip() for x in (m.group(2) or '').split(',') if x.strip()], kv={})
                order.append(cur)
                continue
            if order:
                kv = line.split('=', 1)
                secs[order[-1]]['kv'][kv[0].strip()] = kv[1].strip() if len(kv) > 1 else ''

    read(path)
    flat = {}

    def get(n):
        if n in flat:
            return flat[n]
        d = {}
        for p in secs[n]['parents']:
            d.update(get(p))
        d.update(secs[n]['kv'])
        flat[n] = d
        return d

    for n in secs:
        get(n)
    return flat, secs


# ------------------------------------------------------------------ mod sections
def mod_sections(dirs):
    s = set()
    for L in dirs:
        for dp, _, fn in os.walk(L):
            for f in fn:
                if f.endswith('.ltx'):
                    for line in open(os.path.join(dp, f), 'rb').read().decode('latin1').split('\n'):
                        m = re.match(r'\s*\[([^\]]+)\]', line)
                        if m:
                            s.add(m.group(1))
    return s


# SoC sections that were renamed in the CoP-based add-on
ALIASES = {'killer_outfit': 'merc_outfit', 'wpn_eagle_m1': 'wpn_desert_eagle_m1'}


def map_item(sec, have, report):
    """SoC section -> section that exists in this mod (artifacts have an `_soc` twin with the SoC stats)."""
    for cand in (sec + '_soc', sec, ALIASES.get(sec)):
        if cand in have:
            return cand
    report.setdefault('missing', set()).add(sec)
    return None


# ------------------------------------------------------------------ mod level.spawn
_IDX = {}


def mod_boxes(addon_dir, level):
    out = []
    for dbn in ('gamedata.db0', 'gamedata.db1'):
        dbp = os.path.join(addon_dir, dbn)
        f = open(dbp, 'rb')
        if dbp not in _IDX:
            _IDX[dbp] = xdb.index(f, 0, os.path.getsize(dbp))
        for name, rs, cs, ptr in _IDX[dbp]:
            if name == 'levels\\%s\\level.spawn' % level:
                f.seek(ptr)
                d = f.read(cs)
                if rs != cs:
                    d = xdb.lzo1x(d, rs)
                o = 0
                while o + 8 <= len(d):
                    _, s = struct.unpack_from('<II', d, o); o += 8
                    c = d[o:o + s]; o += s
                    m = re.match(rb'\x01\x00([^\x00]*)\x00([^\x00]*)\x00', c)
                    if m and m.group(1) == b'physic_destroyable_object':
                        pos = struct.unpack_from('<3f', c, m.end() + 2)
                        cd = re.search(rb'(\[[A-Za-z_0-9.]+\][\x09\x0a\x0d\x20-\x7e]*)', c[m.end():])
                        out.append(dict(name=m.group(2).decode('latin1'), pos=pos,
                                        cd=cd.group(1).decode('latin1') if cd else ''))
                return out
    raise SystemExit('level.spawn of %s not found' % level)


def lua_list(items):
    return '{' + ','.join('"%s"' % x if isinstance(x, str) else str(x) for x in items) + '}'


def num(v):
    return ('%.4f' % v).rstrip('0').rstrip('.') if v else '0'


def main():
    ap = argparse.ArgumentParser()
    dl = os.path.join(os.path.expanduser('~'), 'Downloads')
    ap.add_argument('--refs', default=os.path.join(dl, 'SoC_COOP_stashes', 'refs', 'soc1006'))
    ap.add_argument('--addon', default=os.path.join(dl, 'Shadow of COOP 8.0', 'addon_unpacked'))
    ap.add_argument('--mod-configs', nargs='*', default=[
        os.path.join(dl, 'Shadow of COOP 8.0', p) for p in
        ('source_base\\vanilla', 'source_base\\xrmpe_patch', 'source_base\\xrmpe_cop_addon', 'source\\gamedata.db0')])
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'gamedata', 'scripts', 'stash_loot_data.script'))
    a = ap.parse_args()

    for n in ('ph_box_generic', 'ph_box_items_by_communities', 'ph_box_items_by_levels', 'ph_box_items_count'):
        fetch(a.refs, 'config/misc/%s.ltx' % n, n + '.ltx')
    for soc, _ in LEVELS:
        fetch(a.refs, 'spawns/unpack/alife_%s.ltx' % soc, 'alife_%s.ltx' % soc)

    have = mod_sections(a.mod_configs)
    flat, secs = parse_ltx_sections(os.path.join(a.refs, 'ph_box_generic.ltx'))
    report = {}
    cmap = {}

    def mp(sec):
        if sec not in cmap:
            cmap[sec] = map_item(sec, have, report)
        return cmap[sec]

    communities = ['def_box', 'small_box_generic', 'small_box_ussr', 'small_box_nato', 'small_box_army',
                   'small_box_science', 'big_box_generic', 'big_box_dungeons', 'big_box_arsenal']
    comm = {}
    for c in communities:
        d = {}
        for k, v in flat.get(c, {}).items():
            p = 100 * float(v)
            m = mp(k)
            if m and p > 0:
                d[m] = p
        comm[c] = d
    ammo = {mp(k) for k in flat['ammo_sections']}
    ammo.discard(None)
    counts = {}
    for diff in range(4):
        d = {}
        for k, v in flat['item_count_%d' % diff].items():
            nums = [float(x) for x in re.findall(r'[\d.]+', v)]
            m = mp(k)
            if m and nums:
                d[m] = (nums[0], nums[1] if len(nums) > 1 else nums[0])
        counts[diff] = d

    stats = []
    lv_mul, boxes = {}, {}
    for soc, mod in LEVELS:
        lsec = SOC_LEVEL_SECTION.get(soc, soc)
        mul = {}
        for k, v in flat[lsec].items():
            m = mp(k)
            if m and float(v) > 0:
                mul[m] = float(v)
        lv_mul[mod] = mul
        socb = parse_soc_ltx(os.path.join(a.refs, 'alife_%s.ltx' % soc))
        drop = [(e, parse_drop_box(e['cd'])) for e in socb]
        drop = [(e, d) for e, d in drop if d]
        mb = mod_boxes(a.addon, mod)
        # unique nearest matching, closest pairs first
        pairs = sorted((math.dist(e['pos'], m['pos']), i, j) for i, (e, _) in enumerate(drop) for j, m in enumerate(mb))
        used_s, used_m, match = set(), set(), {}
        for dist, i, j in pairs:
            if dist > MATCH_M:
                break
            if i in used_s or j in used_m:
                continue
            used_s.add(i); used_m.add(j); match[i] = j
        lb = {}
        for i, j in match.items():
            kind, val = drop[i][1]
            if kind == 'i':
                items = []
                for k in range(0, len(val), 2):
                    m = mp(val[k])
                    if m:
                        items += [m, val[k + 1]]
                    else:
                        report.setdefault('dropped_explicit', []).append((mod, mb[j]['name'], val[k]))
                lb[mb[j]['name']] = ('i', items, mb[j]['pos'])
            else:
                lb[mb[j]['name']] = ('c', val, mb[j]['pos'])
        boxes[mod] = lb
        mod_db = [m for m in mb if 'drop_box' in m['cd']]
        extra = [m for m in mod_db if m['name'] not in lb]
        stats.append((mod, len(mb), len(drop), len(match), len(mod_db), len(extra)))

    # ---------------------------------------------------------------- emit Lua
    L = ['-- GENERATED by patches/stash_loot/tools/gen_stash_loot.py, do not edit by hand.',
         '-- Data of the original S.T.A.L.K.E.R. SoC 1.0006 breakable boxes ([drop_box] custom_data) matched to the',
         '-- Shadow of COOP box objects by level + position. Item names already mapped to sections that exist in the mod.', '']
    L.append('ammo = {' + ','.join('["%s"]=true' % s for s in sorted(ammo)) + '}')
    L.append('comm = {')
    for c in communities:
        L.append('\t%s = {%s},' % (c, ','.join('["%s"]=%s' % (k, num(v)) for k, v in sorted(comm[c].items()))))
    L.append('}')
    L.append('count = {')
    for d in range(4):
        L.append('\t[%d] = {%s},' % (d, ','.join('["%s"]={%s,%s}' % (k, num(v[0]), num(v[1])) for k, v in sorted(counts[d].items()))))
    L.append('}')
    L.append('level_mul = {')
    for soc, mod in LEVELS:
        L.append('\t%s = {%s},' % (mod, ','.join('["%s"]=%s' % (k, num(v)) for k, v in sorted(lv_mul[mod].items()))))
    L.append('}')
    L.append('-- boxes[level][object name] = {c = community} or {i = {section, count, ...}}, p = spawn position (sanity check)')
    L.append('boxes = {')
    for soc, mod in LEVELS:
        L.append('\t%s = {' % mod)
        for name, (kind, val, pos) in sorted(boxes[mod].items()):
            body = ('c="%s"' % val) if kind == 'c' else ('i=%s' % lua_list(val))
            L.append('\t\t["%s"]={%s,p={%s,%s,%s}},' % (name, body, num(pos[0]), num(pos[1]), num(pos[2])))
        L.append('\t},')
    L.append('}')
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(('\r\n'.join(L) + '\r\n').encode('latin1'))

    print('%-32s %5s %7s %9s %8s %7s' % ('level', 'boxes', 'SoC_db', 'matched', 'mod_db', 'mod_db_not_in_SoC'))
    tot = [0] * 5
    for s in stats:
        print('%-32s %5d %7d %9d %8d %7d' % s)
        for i in range(5):
            tot[i] += s[i + 1]
    print('%-32s %5d %7d %9d %8d %7d' % (('TOTAL',) + tuple(tot)))
    print('items missing in mod (dropped):', sorted(report.get('missing', [])))
    print('explicit items dropped:', report.get('dropped_explicit', []))
    print('wrote', out)


if __name__ == '__main__':
    main()
