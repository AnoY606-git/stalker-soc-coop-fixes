import re, sys
for run in sys.argv[1:]:
    print('==', run)
    cur = None
    res = {}
    for line in open(run + '/client_A/qa_events.log', encoding='utf-8', errors='replace'):
        m = re.search(r'DMG scenario (\S+) mult=([\d.]+)', line)
        if m:
            cur = m.group(1)
            res[cur] = {'mult': m.group(2), 'v': [], 'dead_at': None}
            continue
        m = re.search(r'VOLLEY (\d+) \((\d+) hits in one frame\): hp before=(-?[\d.]+) after-same-frame=(-?[\d.]+) alive=(\w+)', line)
        if m and cur:
            k = int(m.group(1))
            hp = float(m.group(3))
            res[cur]['v'].append(hp)
            if m.group(5) == 'false' and res[cur]['dead_at'] is None:
                res[cur]['dead_at'] = k - 1
    for k, v in res.items():
        print(k, 'mult', v['mult'], 'killed by volley #', v['dead_at'], '| hp before each volley:', ' '.join('%.2f' % x for x in v['v'] if x >= 0)[:80])
