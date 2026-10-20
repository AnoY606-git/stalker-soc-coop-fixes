import sys,struct,os
sys.path.insert(0,'.')
import spawnparse as sp
src=open('modref/levels/coop_l04_darkvalley/level.spawn','rb').read()
tpl=None
for cid,o,sz in sp.chunks(src):
    p=src[o:o+sz]
    if sp.decode(p)['name']=='val_helicopter': tpl=p
assert tpl
BS=chr(92)
oldcfg=('scripts'+BS+'coop_l04_darkvalley'+BS+'val_helicopter.ltx').encode()
assert oldcfg in tpl
dst=open('modref/levels/coop_l08_yantar/level.spawn','rb').read()
n=len(list(sp.chunks(dst)))
out=bytearray(dst)
specs=[('yan_helicopt_1','yan_helicopter_1_a.ltx',(1.0,-81.0,-205.0)),('yan_helicopt_3','yan_helicopter_3_a.ltx',(106.0,-81.0,-207.0))]
for i,(nm,cfg,pos) in enumerate(specs):
    p=bytearray(tpl)
    assert len(nm)==len('val_helicopter')
    newcfg=('scripts'+BS+'coop_l08_yantar'+BS+cfg).encode()
    assert len(newcfg)==len(oldcfg),(len(newcfg),len(oldcfg))
    p=bytearray(bytes(p).replace(b'val_helicopter\0',nm.encode()+b'\0',1).replace(oldcfg,newcfg))
    d=sp.decode(bytes(tpl))
    # position offset: after section\0 name\0 + gid,rp
    o=2
    o=bytes(p).index(b'\0',o)+1; o=bytes(p).index(b'\0',o)+1; o+=2
    struct.pack_into('<3f',p,o,*pos)
    out+=struct.pack('<II',n+i,len(p))+bytes(p)
open('lvl/levels/coop_l08_yantar/level.spawn','wb').write(out)
t=open('lvl/levels/coop_l08_yantar/level.spawn','rb').read()
for cid,o,sz in list(sp.chunks(t))[-3:]:
    print(cid,sz,sp.decode(t[o:o+sz]))
