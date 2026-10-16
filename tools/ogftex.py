import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xdb
BS = chr(92)
game = sys.argv[1]
prefix = sys.argv[2].lower()
dbs = sorted(glob.glob(os.path.join(game, 'resources', '*.db*'))) + sorted(glob.glob(os.path.join(game, 'patches', '*.db*')))
best = {}
for dbp in dbs:
    f = open(dbp, 'rb')
    for n, rs, cs, ptr in xdb.index(f, 0, os.path.getsize(dbp)):
        nl = n.lower()
        if nl.startswith(prefix) and nl.endswith('.ogf') and 'face' not in nl and 'unique' not in nl:
            f.seek(ptr); d = f.read(cs)
            if rs != cs: d = xdb.lzo1x(d, rs)
            tex = sorted(set(t.decode() for t in re.findall(rb'act[\\/][a-z0-9_\\/]+', d)))
            best[nl] = (os.path.basename(dbp), tex)
for k, v in sorted(best.items()):
    print(k.split(BS)[-1], v[0], v[1])
