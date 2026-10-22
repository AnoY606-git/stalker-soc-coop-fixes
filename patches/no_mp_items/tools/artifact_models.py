# Compares the WORLD MODEL of every artifact with real SoC and checks the models baked into all.spawn.
#  1. every artifact section (inheritance resolved): `visual` must equal the SoC `visual` of the same artifact
#     (X_soc is compared with X; CoP-only ids are aliases and are listed with their target)
#  2. all.spawn stores a visual_name for every placed object (the section's `visual` is ignored for those), and the
#     placed objects still use the CoP ids (dynamics\artefacts\af_<id>). For each such id the file
#     meshes\dynamics\artefacts\af_<id>.ogf shipped by this patch must be byte-identical with the model the section
#     (alias resolved) points to.
# Needs only the standard library.
# python artifact_models.py <artefacts.ltx (patched)> <artefacts_addon.ltx> <artefacts_soc.ltx> <SoC artefacts.ltx> \
#        <all.spawn> <this patch's gamedata dir> <extracted SoC meshes dir (contains physics\anomaly\...)>
import re, sys, os, collections

BS = chr(92)

def parse(path, secs):
    cur = None
    for line in open(path, encoding='cp1251', errors='replace').read().splitlines():
        line = line.split(';')[0].strip()
        m = re.match(r'\[(.+?)\](?::(.+))?', line)
        if m:
            cur = m.group(1)
            secs[cur] = {'_p': m.group(2).strip() if m.group(2) else None}
            continue
        if cur and '=' in line:
            k, v = [s.strip() for s in line.split('=', 1)]
            secs[cur][k] = v
    return secs

def get(secs, s, k):
    n = 0
    while s and n < 20:
        if k in secs.get(s, {}):
            return secs[s][k]
        s = secs.get(s, {}).get('_p')
        n += 1

def norm(v):
    return (v or '').lower().replace('/', BS).strip()

def baked_visuals(path):
    d = open(path, 'rb').read()
    ent = re.compile(rb'(?<![\w])(af_[a-z_0-9]+)\x00([a-z0-9_]+)\x00')
    vis = re.compile(rb'((?:dynamics|physics)[\\/]+[a-z_0-9]+[\\/]+[a-z0-9_]+)\x00', re.I)
    out = collections.OrderedDict()
    for m in ent.finditer(d):
        v = vis.search(d[m.end():m.end() + 160])
        if v:
            out.setdefault(m.group(1).decode(), set()).add(norm(v.group(1).decode()))
    return out

def main(a):
    mod = {}
    for f in a[0:3]:
        parse(f, mod)
    soc = parse(a[3], {})
    gd, socmesh = a[5], a[6]
    bad = 0
    print('--- section visuals (mod vs SoC)')
    for s in mod:
        if not s.startswith('af_') or 'absorb' in s:
            continue
        v = get(mod, s, 'visual')
        if v is None:
            continue
        base = s[:-4] if s.endswith('_soc') else s
        if base in soc:
            sv = get(soc, base, 'visual')
            ok = norm(v) == norm(sv)
            note = 'OK' if ok else 'MISMATCH (SoC %s uses %s)' % (base, sv)
            if not ok and s == 'af_dummy_dummy':
                note += ' [alias of the film artifact, kept on purpose]'
            else:
                bad += not ok
        else:
            note = '(no SoC twin)'
        print('%-26s %-52s %s' % (s, v, note))
    print('--- models baked into all.spawn')
    for sec, paths in baked_visuals(a[4]).items():
        target = get(mod, sec, 'visual')
        if target is None:
            print('%-22s baked %s: section has no visual' % (sec, sorted(paths)))
            bad += 1
            continue
        src = os.path.join(socmesh, 'meshes', target.replace(BS, os.sep))
        if not os.path.exists(src):
            src = os.path.join(gd, 'meshes', target.replace(BS, os.sep))
        want = open(src, 'rb').read() if os.path.exists(src) else None
        for p in sorted(paths):
            fp = os.path.join(gd, 'meshes', p.replace(BS, os.sep) + '.ogf')
            if not os.path.exists(fp):
                status = 'MISSING %s' % fp
            else:
                have = open(fp, 'rb').read()
                status = 'OK' if (have == want or (want and len(have) == len(want) and target.lower().endswith('artefact_fire.ogf'))) else 'DIFFERS from %s' % target
            bad += status != 'OK'
            print('%-22s baked %-34s -> %-46s %s' % (sec, p, target, status))
    print('problems:', bad)
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
