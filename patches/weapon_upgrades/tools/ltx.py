import re,os,sys
def parse_file(path, secs, order, seen=None):
    seen = seen if seen is not None else set()
    txt = open(path, encoding='cp1251', errors='replace').read()
    cur=None
    for raw in txt.splitlines():
        line = raw.split(';')[0].strip() if not raw.strip().startswith('#') else raw.strip()
        if not line: continue
        if line.startswith('#include'):
            m=re.match(r'#include\s+"([^"]+)"',line)
            if m: yield ('include', m.group(1))
            continue
        m=re.match(r'\[([^\]]+)\]\s*(?::\s*(.*))?$',line)
        if m:
            cur=m.group(1).strip()
            par=[p.strip() for p in (m.group(2) or '').split(',') if p.strip()]
            secs.setdefault(cur,{'_parents':par,'_kv':{},'_file':path})
            if cur in secs and secs[cur]['_file']!=path:
                secs[cur]={'_parents':par,'_kv':secs[cur]['_kv'],'_file':path}
            secs[cur]['_parents']=par or secs[cur]['_parents']
            continue
        if cur is None: continue
        if '=' in line:
            k,v=line.split('=',1); secs[cur]['_kv'][k.strip()]=v.strip()
        else:
            secs[cur]['_kv'][line]=''
def load(roots, entry):
    """roots: list of dirs, later overrides earlier (file-level). entry: relative path"""
    secs={}
    def find(rel):
        for r in reversed(roots):
            p=os.path.join(r,rel.replace(chr(92),'/'))
            if os.path.exists(p): return p
    def do(rel, depth=0, base=''):
        rel=rel.replace(chr(92),'/')
        p=find(base+rel) or find(rel)
        if not p: print('MISSING include',base+rel,file=sys.stderr); return
        nb=(base+rel).rsplit('/',1)[0]+'/' if '/' in (base+rel) else ''
        if not find(base+rel): nb=rel.rsplit('/',1)[0]+'/' if '/' in rel else ''
        for ev in parse_file(p,secs,None):
            if ev[0]=='include': do(ev[1],depth+1,nb)
    do(entry)
    return secs
def get(secs,sec,key,default=None):
    s=secs.get(sec)
    if not s: return default
    if key in s['_kv']: return s['_kv'][key]
    for p in s['_parents']:
        r=get(secs,p,key,None)
        if r is not None: return r
    return default
