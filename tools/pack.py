# Build an uncompressed X-Ray (CoP) .db from a folder whose contents map to gamedata\
import sys, os, struct, zlib

BS = chr(92)
src, out = sys.argv[1], sys.argv[2]
hdr = ('[header]\r\nauto_load = true\r\ncreator = "GSC/xrMPE team"\r\n'
       'entry_point = $fs_root$' + BS + 'gamedata' + BS + '\r\n'
       'level_name = single\r\nlevel_ver = 1.0\r\nlink = vk.com/xr_mpe\r\n').encode('ascii')

files, dirs = [], set()
for root, ds, fs in os.walk(src):
    for fn in fs:
        p = os.path.join(root, fn)
        rel = os.path.relpath(p, src).replace(os.sep, BS)
        files.append((rel, p))
        parts = rel.split(BS)[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add(BS.join(parts[:i]) + BS)
files.sort()

data_off = 8 + len(hdr) + 8  # absolute offset of chunk 0 payload
blob = bytearray()
ents = [(d, 0, 0, 0, 0) for d in sorted(dirs)]
for rel, p in files:
    b = open(p, 'rb').read()
    ents.append((rel, len(b), len(b), zlib.crc32(b) & 0xffffffff, data_off + len(blob)))
    blob += b

idx = bytearray()
for name, rs, cs, crc, ptr in ents:
    nb = name.encode('cp1251')
    idx += struct.pack('<HIII', len(nb) + 16, rs, cs, crc) + nb + struct.pack('<I', ptr)

with open(out, 'wb') as f:
    f.write(struct.pack('<II', 666, len(hdr)) + hdr)
    f.write(struct.pack('<II', 0, len(blob)) + blob)
    f.write(struct.pack('<II', 1, len(idx)) + idx)
print('packed', len(files), 'files,', len(dirs), 'dirs ->', out, os.path.getsize(out), 'bytes')
