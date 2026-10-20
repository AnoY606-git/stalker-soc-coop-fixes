# Lists files shipped by more than one patch (build.py copies patches in sorted order, so the last one silently wins).
# Usage: python tools/check_conflicts.py [patch names to skip...]
import os, sys, hashlib

here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
skip = set(sys.argv[1:])
owners = {}
for fix in sorted(os.listdir(os.path.join(here, 'patches'))):
    root = os.path.join(here, 'patches', fix, 'gamedata')
    if fix in skip or not os.path.isdir(root):
        continue
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).lower()
            owners.setdefault(rel, []).append((fix, hashlib.md5(open(p, 'rb').read()).hexdigest()))
n = 0
for rel, lst in sorted(owners.items()):
    if len(lst) > 1:
        same = len({h for _, h in lst}) == 1
        print('%-70s %s%s' % (rel, ', '.join(f for f, _ in lst), '  (identical)' if same else ''))
        n += 1
print(n, 'files shipped by more than one patch')
