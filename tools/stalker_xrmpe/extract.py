import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import xdb
outdir=sys.argv[1];exts=tuple(sys.argv[2].split(','));dbs=sys.argv[3:]
tot=0
for dbp in dbs:
    f=open(dbp,'rb');ents=xdb.index(f,0,os.path.getsize(dbp));n=0
    for name,rs,cs,ptr in ents:
        if rs==0 or not name.lower().endswith(exts): continue
        f.seek(ptr);data=f.read(cs)
        if rs!=cs: data=xdb.lzo1x(data,rs)
        dst=os.path.join(outdir,name.replace(chr(92),os.sep))
        os.makedirs(os.path.dirname(dst),exist_ok=True);open(dst,'wb').write(data);n+=1
    print(os.path.basename(dbp),len(ents),'entries,',n,'extracted');tot+=n
print('total',tot)
