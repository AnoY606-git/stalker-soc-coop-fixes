import re, sys, os, collections
# usage: an.py <resultdir>   prints per client: segments of body id and whether the last dump of the segment matches the server's EXPECT
d = sys.argv[1]
def rd(p):
    try:
        return open(p, 'rb').read().replace(b'\0', b'').decode('utf-8', 'replace').splitlines()
    except Exception:
        return []
exp = {}
for l in rd(os.path.join(d, 'client_S', 'qa_events.log')):
    m = re.search(r'SLOT EXPECT (\S+) (.*)$', l)
    if m:
        exp[m.group(1).lower()] = m.group(2)
print('EXPECT', exp)
def key_from_dump(l):
    sl = {}
    for m in re.finditer(r'\bs(\d+)=(\w+)#(\d+)', l.split('| inv:')[0]):
        sl[int(m.group(1))] = (m.group(2), int(m.group(3)))
    inv = l.split('| inv:')[1] if '| inv:' in l else ''
    cnt = collections.Counter(re.findall(r'(\w+?)#\d+\(p', inv))
    return sl, cnt
def exp_key(e):
    sl = {}
    for m in re.finditer(r's(\d+)=(\w+)#(\d+)', e.split(';m=')[0]):
        sl[int(m.group(1))] = (m.group(2), int(m.group(3)))
    inv = e.split('inv=')[1]
    cnt = collections.Counter()
    for t in inv.split(','):
        m = re.match(r'(\w+?)x(\d+)$', t)
        cnt[m.group(1)] += int(m.group(2))
    return sl, cnt
for cl in sorted(x for x in os.listdir(d) if x.startswith('client_') and x != 'client_S'):
    lines = [l for l in rd(os.path.join(d, cl, 'qa_events.log')) if ' cli name=' in l]
    segs = []
    for l in lines:
        m = re.search(r'cli name=(\S+) id=(\d+)', l)
        if not m: continue
        if segs and segs[-1][0] == m.group(2): segs[-1][2] = l; segs[-1][3] += 1
        else: segs.append([m.group(2), m.group(1), l, 1])
    # expected name: from the harness name (qaA -> qaa)
    nm = 'qa' + cl.split('_')[1].lower()
    e = exp.get(nm)
    print(cl, 'expect for', nm, 'found' if e else 'MISSING')
    for sid, name, last, n in segs:
        sl, cnt = key_from_dump(last)
        ok = None
        if e:
            esl, ecnt = exp_key(e)
            ok = all(sl.get(s) == esl[s] for s in (2, 3, 7)) and cnt == ecnt
        print('  body', sid, name, 'dumps', n, 'last dump matches expect' if ok else ('last dump DIFFERS' if ok is False else '?'), '| t=', last[:9])
