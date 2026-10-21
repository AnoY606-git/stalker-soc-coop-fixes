# Lists every artifact section (inheritance resolved) with inv_name, grid cell and whether its icon in the mod texture matches
# the real SoC icon. Needs Pillow + numpy.
# python artifact_icons.py <artefacts.ltx (patched)> <artefacts_addon.ltx> <artefacts_soc.ltx> <SoC artefacts.ltx> \
#        <mod ui_icon_equipment.dds> <SoC ui_icon_equipment.dds>
import re, sys
import numpy as np
from PIL import Image

def parse(path, secs):
    cur = None
    for line in open(path, encoding='cp1251', errors='replace').read().splitlines():
        line = line.split(';')[0].strip()
        m = re.match(r'\[(.+?)\](?::(.+))?', line)
        if m:
            cur = m.group(1); secs[cur] = {'_p': m.group(2)}; continue
        if cur and '=' in line:
            k, v = [s.strip() for s in line.split('=', 1)]; secs[cur][k] = v
    return secs

def get(secs, s, k):
    while s:
        if k in secs.get(s, {}): return secs[s][k]
        s = secs.get(s, {}).get('_p')

def cell(im, x, y):
    return np.asarray(im.crop((x * 50, y * 50, x * 50 + 50, y * 50 + 50))).astype(int)

def dist(a, b):
    m = (a[..., 3] > 128) & (b[..., 3] > 128)
    return abs(a - b)[m][:, :3].mean() if m.any() else 999

def main(a):
    mod = {}
    for f in a[0:3]: parse(f, mod)
    soc = parse(a[3], {})
    mt = Image.open(a[4]).convert('RGBA'); st = Image.open(a[5]).convert('RGBA')
    socicons = {t: cell(st, int(get(soc, t, 'inv_grid_x')), int(get(soc, t, 'inv_grid_y')))
                for t in soc if t.startswith('af_') and 'absorb' not in t and get(soc, t, 'inv_grid_x')}
    bad = 0
    for s in mod:
        if 'absorb' in s or not s.startswith('af_') or get(mod, s, 'inv_grid_x') is None: continue
        x, y = int(get(mod, s, 'inv_grid_x')), int(get(mod, s, 'inv_grid_y'))
        c = cell(mt, x, y)
        base = s[:-4] if s.endswith('_soc') else s
        best = min(socicons, key=lambda t: dist(c, socicons[t]))
        d = dist(c, socicons[best])
        status = ''
        if base in socicons:
            status = 'OK' if best == base and d < 20 else 'MISMATCH (icon is %s d=%.0f; SoC %s uses %s,%s)' % (
                best, d, base, get(soc, base, 'inv_grid_x'), get(soc, base, 'inv_grid_y'))
            bad += status != 'OK'
        print('%-26s %-30s %2d,%-2d %s' % (s, get(mod, s, 'inv_name'), x, y, status))
    print('mismatches:', bad)
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
