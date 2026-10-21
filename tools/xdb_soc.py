# Reader for the Steam SoC 1.0006 archives (gamedata.db0..dbd): index = trivial_encryptor substitution + LZ-Huffman, data = LZO1X.
# python -I xdb_soc.py <regex on the file name> list            lists matches in all archives
# python -I xdb_soc.py <regex> x <outdir>                      extracts matches (later archives win); caches indexes as idx_*.pkl in the cwd
import sys,os,struct,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import xdb
PARAMS=[(1024,6011979,24031979),(2048,20091958,20031955)]
def make_decoder(it,ts,es):
    a=list(range(256)); st=[ts]
    def rnd(rng):
        st[0]=(0x08088405*st[0]+1)&0xffffffff
        return (st[0]*rng)>>32
    for _ in range(it):
        j=rnd(256);k=rnd(256)
        while j==k:k=rnd(256)
        a[j],a[k]=a[k],a[j]
    back=[0]*256
    for i in range(256):back[a[i]]=i
    def dec(raw):
        st[0]=es;out=bytearray()
        for b in raw: out.append(back[b^(rnd(256)&0xff)])
        return bytes(out)
    return dec
DECODERS=[make_decoder(*p) for p in PARAMS]
def pick(raw,size):
    for d in DECODERS:
        r=d(raw);real=struct.unpack('<I',r[:4])[0]
        if 0<real<50000000: print('decoder ok',real,flush=True);return r
    raise ValueError('no decoder')
def index(f,size):
    pos=0
    while pos<size:
        f.seek(pos);cid,csz=struct.unpack('<II',f.read(8))
        if cid&0x7fffffff==1:
            raw=f.read(csz)
            if cid&0x80000000:
                raw=pick(raw,size)
                real=struct.unpack('<I',raw[:4])[0];raw=xdb.lzhuf_decode(raw[4:],real)
            break
        pos+=8+csz
    ents=[];i=0
    while i<len(raw):
        bs,=struct.unpack_from('<H',raw,i); i+=2
        rs,cs,crc=struct.unpack_from('<III',raw,i)
        name=raw[i+12:i+bs-4].decode('cp1251');ptr=struct.unpack_from('<I',raw,i+bs-4)[0]
        ents.append((name,rs,cs,ptr));i+=bs
    return ents
def read(f,e):
    name,rs,cs,ptr=e
    f.seek(ptr);d=f.read(cs)
    if rs!=cs:d=xdb.lzo1x(d,rs)
    return d
if __name__=='__main__':
    pat=re.compile(sys.argv[1],re.I)
    S=r'C:\Program Files (x86)\Steam\steamapps\common\STALKER Shadow of Chernobyl'
    mode=sys.argv[2]; out=sys.argv[3] if len(sys.argv)>3 else None
    for fn in sorted(os.listdir(S)):
        if not fn.startswith('gamedata.db'):continue
        p=os.path.join(S,fn);f=open(p,'rb')
        import pickle
        cp='idx_'+fn+'.pkl'
        try:
            ents=pickle.load(open(cp,'rb')) if os.path.exists(cp) else index(f,os.path.getsize(p))
            pickle.dump(ents,open(cp,'wb'))
        except Exception as ex: print(fn,'ERR',ex);continue
        print(fn,len(ents),flush=True)
        for e in ents:
            if pat.search(e[0]):
                if mode=='list':print(fn,e[0],e[1],sep='\t',flush=True)
                else:
                    d=read(f,e);dst=os.path.join(out,e[0].replace(chr(92),os.sep));os.makedirs(os.path.dirname(dst),exist_ok=True);open(dst,'wb').write(d);print('x',e[0],len(d),flush=True)
