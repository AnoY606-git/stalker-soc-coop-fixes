# Find model files across all game archives and report triangles / LOD (SWI) info.
import sys, os, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xdb

game = sys.argv[1]
want = [w.lower() for w in sys.argv[2:]]
dbs = sorted(glob.glob(os.path.join(game, 'resources', '*.db*'))) + sorted(glob.glob(os.path.join(game, 'patches', '*.db*')))
# folder with the unpacked coop.addon members gamedata.db0 / gamedata.db1 (tar of coop.addon extracted), env SOC_ADDON_UNPACKED
ADDON_UNPACKED = os.environ.get('SOC_ADDON_UNPACKED', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'addon_unpacked'))
addon_dbs = [os.path.join(ADDON_UNPACKED, n) for n in ('gamedata.db0', 'gamedata.db1')]
dbs += [p for p in addon_dbs if os.path.exists(p)]

def chunks(b, off=0, end=None):
    end = len(b) if end is None else end
    while off + 8 <= end:
        cid, sz = struct.unpack_from('<II', b, off)
        yield cid & 0x7fffffff, b[off + 8: off + 8 + sz]
        off += 8 + sz

def analyse(b):
    tris = 0; swi = 0; kids = 0; lods = None
    def walk(data, depth=0):
        nonlocal tris, swi, kids, lods
        for cid, c in chunks(data):
            if cid == 4 and len(c) >= 4:   # OGF_INDICES
                tris += struct.unpack_from('<I', c)[0] // 3
            elif cid == 6:                 # OGF_SWIDATA (progressive LOD)
                swi += 1
            elif cid == 23:                # OGF_S_LODS
                lods = c[:80]
            elif cid == 9:                 # OGF_CHILDREN
                for _, child in chunks(c):
                    kids += 1
                    walk(child, depth + 1)
    walk(b)
    return tris, kids, swi, lods

found = {}
for dbp in dbs:
    try:
        f = open(dbp, 'rb'); ents = xdb.index(f, 0, os.path.getsize(dbp))
    except Exception as e:
        continue
    for n, rs, cs, ptr in ents:
        nl = n.lower()
        if nl.endswith('.ogf') and any(w in nl for w in want):
            f.seek(ptr); d = f.read(cs)
            if rs != cs: d = xdb.lzo1x(d, rs)
            found[nl] = (os.path.basename(dbp), analyse(d), rs)
for n in sorted(found):
    db, (t, k, s, l), size = found[n]
    print(f'{n:60s} {db:28s} tris={t:7d} meshes={k:3d} lod_meshes={s:3d} size={size//1024}KB lods={l!r}')
