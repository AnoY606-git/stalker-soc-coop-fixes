import re,sys
for run in sys.argv[1:]:
    print('==',run)
    cur=None; res={}
    for line in open(run+'/client_A/qa_events.log',encoding='utf-8',errors='replace'):
        m=re.search(r'DMG scenario (\S+) mult=([\d.]+)',line)
        if m: cur=m.group(1); res[cur]={'mult':m.group(2),'hits':[], 'dead_at':None}; continue
        m=re.search(r'DMG HIT (\d+): hp before=(-?[\d.]+) after-same-frame=(-?[\d.]+) alive=(\w+)',line)
        if m and cur:
            k=int(m.group(1)); hp=float(m.group(2)); alive=m.group(4)
            res[cur]['hits'].append((k,hp,alive))
            if alive=='false' and res[cur]['dead_at'] is None: res[cur]['dead_at']=k-1
    for k,v in res.items():
        hp=[h[1] for h in v['hits'] if h[1]>=0]
        print(k,'mult',v['mult'],'killed by hit #',v['dead_at'],'| hp before each hit:',' '.join('%.2f'%x for x in hp[:10]))
