# Byte-exact round trip check of a packed .db against the folder it was built from.
#   python verify_db.py <db> <srcdir>
# Every entry is read back with xdb.py (its own LZO1X decompressor, the reader the project already trusts) and compared with the
# source file; the CRC32 in the index is checked too. When python-lzo is importable (tools\.lzovenv) every compressed entry is
# ALSO decompressed with the standard library decoder and compared. Exit 0 = all identical.
import os, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xdb  # noqa: E402


def entries_with_crc(f, size):
    pos = 0
    raw = None
    while pos < size:
        f.seek(pos)
        cid, csz = struct.unpack('<II', f.read(8))
        if cid & 0x7fffffff == 1:
            raw = f.read(csz)
            if cid & 0x80000000:
                real = struct.unpack('<I', raw[:4])[0]
                raw = xdb.lzhuf_decode(raw[4:], real)
            break
        pos += 8 + csz
    ents, i = [], 0
    while i < len(raw):
        bs, rs, cs, crc = struct.unpack_from('<HIII', raw, i)
        name = raw[i + 14:i + bs - 2].decode('cp1251')
        ptr = struct.unpack_from('<I', raw, i + bs - 2)[0]
        ents.append((name, rs, cs, crc, ptr))
        i += bs + 2
    return ents


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    db, src = sys.argv[1], sys.argv[2]
    try:
        import lzo
    except ImportError:
        lzo = None
    size = os.path.getsize(db)
    bad, n_files, n_comp, n_raw = [], 0, 0, 0
    seen = set()
    with open(db, 'rb') as f:
        for name, rs, cs, crc, ptr in entries_with_crc(f, size):
            if rs == 0 and cs == 0 and crc == 0 and name.endswith('\\'):
                continue
            n_files += 1
            seen.add(name)
            p = os.path.join(src, name.replace('\\', os.sep))
            if not os.path.isfile(p):
                bad.append((name, 'not in source folder'))
                continue
            want = open(p, 'rb').read()
            f.seek(ptr)
            stored = f.read(cs)
            if len(stored) != cs or ptr + cs > size:
                bad.append((name, 'entry runs past the end of the db'))
                continue
            if rs != cs:
                n_comp += 1
                got = xdb.lzo1x(stored, rs)
                if lzo is not None and lzo.decompress(stored, False, rs) != want:
                    bad.append((name, 'python-lzo decompress differs'))
                    continue
            else:
                n_raw += 1
                got = stored
            if got != want:
                bad.append((name, 'xdb.py decompress differs (%d vs %d bytes)' % (len(got), len(want))))
            elif zlib.crc32(want) & 0xffffffff != crc:
                bad.append((name, 'crc mismatch'))
    missing = []
    for root, _, fs in os.walk(src):
        for fn in fs:
            rel = os.path.relpath(os.path.join(root, fn), src).replace(os.sep, '\\')
            if rel not in seen:
                missing.append(rel)
    for m in missing:
        bad.append((m, 'source file missing from the db'))
    print('verify_db: %d files (%d compressed, %d raw)%s, %d problems' % (
        n_files, n_comp, n_raw, ', second decoder: python-lzo' if lzo else '', len(bad)))
    for name, why in bad[:20]:
        print('  BAD', name, why)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
