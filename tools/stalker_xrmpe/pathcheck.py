import sys, os, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xdb

BS = chr(92)
P, D = sys.argv[1], sys.argv[2]
levels = sys.argv[3:]
want = {'levels' + BS + L + BS + 'level.game': L for L in levels}
games = {}
for db in ('gamedata.db0', 'gamedata.db1'):
    p = os.path.join(D, db)
    f = open(p, 'rb')
    for n, rs, cs, ptr in xdb.index(f, 0, os.path.getsize(p)):
        if n in want:
            f.seek(ptr)
            d = f.read(cs)
            if rs != cs:
                d = xdb.lzo1x(d, rs)
            games[want[n]] = d

for L in levels:
    g = games.get(L)
    if g is None:
        print(L, 'level.game not found')
        continue
    names = set(re.findall(rb'[A-Za-z_0-9]{4,}', g))
    used = {}
    for fpath in glob.glob(P + '/source/gamedata.db0/configs/scripts/' + L + '/**/*.ltx', recursive=True):
        for line in open(fpath, 'rb').read().split(b'\n'):
            line = line.split(b';')[0]
            toks = []
            m = re.match(rb'\s*(path_walk|path_look|path_move|path_fly|point|look|path)\s*=\s*([A-Za-z_0-9]+)', line)
            if m:
                toks.append(m.group(2))
            for a in re.findall(rb'=(?:xrmpe_teleport_[a-z_]+|spawn_object|teleport_actor|teleport_squad)\(([^)]*)\)', line):
                toks += [t for t in re.split(rb'[:,]', a) if t]
            for t in toks:
                if t not in names and not t.isdigit() and t not in (b'none', b'nil') and not t.startswith(b'wpn_'):
                    used.setdefault(t.decode(), set()).add(os.path.basename(fpath))
    print(L, 'paths in level:', len(names), '| unresolved:', len(used))
    for k, v in list(used.items())[:20]:
        print('   ', k, sorted(v)[:2])
