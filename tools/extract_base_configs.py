import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'stalker_xrmpe'))
import xdb
out = sys.argv[1]   # usage: python extract_base_configs.py OUTDIR (writes OUTDIR/configs/**.ltx)
roots = [r'C:\X-Ray Multiplayer Extension\game\resources', r'C:\X-Ray Multiplayer Extension\game\patches']
n = 0
for r in roots:
    for f in sorted(os.listdir(r)):
        p = os.path.join(r, f)
        if not os.path.isfile(p):
            continue
        try:
            fh = open(p, 'rb')
            ents = xdb.index(fh, 0, os.path.getsize(p))
        except Exception:
            continue
        for name, rs, cs, ptr in ents:
            ln = name.lower().replace('\\', '/')
            if not ln.startswith('config') or not ln.endswith('.ltx'):
                continue
            fh.seek(ptr)
            d = fh.read(cs)
            if rs != cs:
                d = xdb.lzo1x(d, rs)
            dst = os.path.join(out, ln)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(d)
            n += 1
print('extracted', n)
