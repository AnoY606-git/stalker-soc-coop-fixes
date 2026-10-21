# Check that every .ogf shipped by our patches (all patches, or a staged gamedata dir) has all of the
# ltx files its user data #includes (and their nested #includes) present in the patches or in the
# base archives (xrMPE resources/patches, coop.addon, other xrMPE addons, extracted add-on gamedata).
# Includes resolve against configs\ (e.g. "models\capture\x.ltx" -> configs\models\capture\x.ltx).
# Usage: python -I tools\check_ogf_includes.py [--stage DIR] [--game DIR]
import sys, os, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import xdb

game = r'C:\X-Ray Multiplayer Extension\game'
stage = None
a = sys.argv[1:]
while a:
    if a[0] == '--stage': stage = a[1]; a = a[2:]
    elif a[0] == '--game': game = a[1]; a = a[2:]
    else: a = a[1:]

INC = re.compile(rb'#include\s+"([^"]+)"', re.I)

BS = chr(92)
def norm(p): return p.replace('/', BS).lower().lstrip(BS)

# --- gamedata roots from our patches (or one staged dir)
roots = [stage] if stage else sorted(glob.glob(os.path.join(ROOT, 'patches', '*', 'gamedata')))
patch_files = {}   # normalized relative path -> absolute path
for r in roots:
    for dp, _, fns in os.walk(r):
        for fn in fns:
            ap = os.path.join(dp, fn)
            patch_files[norm(os.path.relpath(ap, r))] = ap

# --- base archives
base = {}  # normalized name -> (file, off, entry)
def add_arch(p, off, size):
    try:
        f = open(p, 'rb'); ents = xdb.index(f, off, size); f.close()
    except Exception:
        return
    for n, rs, cs, ptr in ents:
        base[norm(n)] = (p, off, rs, cs, ptr)
srcs = sorted(glob.glob(os.path.join(game, 'resources', '*.db*')) + glob.glob(os.path.join(game, 'patches', '*.db*')))
for p in srcs: add_arch(p, 0, os.path.getsize(p))
for p in glob.glob(os.path.join(game, 'addons', '*.addon')):
    if os.path.basename(p).lower().startswith('qalane'): continue
    try: mem = xdb.tar_members(p)
    except Exception: continue
    for n, (o, s) in mem.items():
        if '.db' in n and not n.startswith('zzz'): add_arch(p, o, s)
for p in [x for x in os.environ.get('ADDON_UNPACKED', '').split(os.pathsep) if x]:
    for n in ('gamedata.db0', 'gamedata.db1'):
        q = os.path.join(p, n)
        if os.path.exists(q): add_arch(q, 0, os.path.getsize(q))

def read_file(key):
    if key in patch_files: return open(patch_files[key], 'rb').read()
    if key in base:
        p, off, rs, cs, ptr = base[key]
        with open(p, 'rb') as f:
            f.seek(off + ptr); d = f.read(cs)
        return d if rs == cs else xdb.lzo1x(d, rs)
    return None

def has(key): return key in patch_files or key in base

def resolve_includes(data, seen, chain, out):
    for m in INC.finditer(data):
        raw = m.group(1).decode('cp1251', 'replace')
        key = 'configs' + BS + norm(raw)
        if key in seen: continue
        seen.add(key)
        if not has(key):
            out.append((raw, ' -> '.join(chain)))
            continue
        sub = read_file(key)
        if sub: resolve_includes(sub, seen, chain + [raw], out)

bad = 0; total = 0; withinc = 0
for key in sorted(patch_files):
    if not key.endswith('.ogf') or not key.startswith('meshes' + BS): continue
    total += 1
    data = open(patch_files[key], 'rb').read()
    if not INC.search(data): continue
    withinc += 1
    miss = []
    resolve_includes(data, set(), [], miss)
    for raw, via in miss:
        bad += 1
        print('MISSING %s : includes %s%s' % (key, raw, (' (via ' + via + ')') if via else ''))
print('ogf files checked: %d, with includes: %d, missing include files: %d' % (total, withinc, bad))
print('base archives indexed: %d names' % len(base))
sys.exit(1 if bad else 0)
