# Build an X-Ray (CoP) .db from a folder whose contents map to gamedata\
#
#   python pack.py <srcdir> <out.db> [--compress | --no-compress] [--level N] [--quiet]
#
# --compress   (default OFF here, build.py turns it ON for releases) stores every file LZO1X-compressed (the engine reads an entry as
#              compressed when size_compressed != size_real); a file stays RAW when compression does not make it smaller.
#              Needs the python-lzo package. It is looked up in the running Python, then in tools\.lzovenv (created on first
#              use: `python -m venv tools\.lzovenv` + `pip install python-lzo`).
# --level N    LZO level: 1 = LZO1X-1 (fast), 9 = LZO1X-999 (best, default). Output is standard LZO1X: lzo1x_decompress_safe reads it.
#
# Why: coop.addon is a tar whose 32-bit engine cannot map data past 4 GiB; a raw db of more than about 73 MB breaks every level
# load (see stalker.md section 3). Compression is what keeps the release under that line.
import sys, os, struct, zlib, subprocess

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, '.lzovenv')
VENV_PY = os.path.join(VENV, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(VENV, 'bin', 'python')


def load_lzo():
    """Return the lzo module, re-running this script inside tools\\.lzovenv when the current Python has no python-lzo."""
    try:
        import lzo
        return lzo
    except ImportError:
        pass
    if os.environ.get('SOC_PACK_REEXEC'):
        sys.exit('pack.py: python-lzo is missing even inside ' + VENV + ' (pip install python-lzo)')
    if not os.path.exists(VENV_PY):
        print('pack.py: creating ' + VENV + ' and installing python-lzo (once)', flush=True)
        subprocess.check_call([sys.executable, '-m', 'venv', VENV])
        subprocess.check_call([VENV_PY, '-m', 'pip', 'install', '--quiet', 'python-lzo==1.15'])
    env = dict(os.environ, SOC_PACK_REEXEC='1')
    sys.exit(subprocess.call([VENV_PY, os.path.abspath(__file__)] + sys.argv[1:], env=env))


def lzo_pack(lzo, b, level):
    """Compress b to a raw LZO1X stream (no python-lzo header). Returns None when it would not shrink."""
    if len(b) < 64:
        return None
    c = lzo.compress(b, 1, False)
    if level > 1 and len(c) < len(b) * 0.97:       # already-incompressible data (ogg, ogm, jpg dds) skips the slow pass
        c9 = lzo.compress(b, level, False)
        if len(c9) < len(c):
            c = c9
    if len(c) >= len(b):
        return None
    return c


def main(argv):
    pos, level, compress, quiet = [], 9, False, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--compress':
            compress = True
        elif a == '--no-compress':
            compress = False
        elif a == '--quiet':
            quiet = True
        elif a == '--level':
            level = int(argv[i + 1])
            i += 1
        elif a.startswith('--level='):
            level = int(a[8:])
        elif a.startswith('--'):
            sys.exit('pack.py: unknown option ' + a)
        else:
            pos.append(a)
        i += 1
    if len(pos) != 2:
        sys.exit(__doc__)
    src, out = pos
    lzo = load_lzo() if compress else None

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
    raw_total = 0
    n_comp = 0
    for rel, p in files:
        b = open(p, 'rb').read()
        raw_total += len(b)
        stored = b
        if compress:
            c = lzo_pack(lzo, b, level)
            if c is not None:
                if lzo.decompress(c, False, len(b)) != b:     # never ship a stream that does not round-trip
                    sys.exit('pack.py: LZO round trip failed for ' + rel)
                stored = c
                n_comp += 1
        ents.append((rel, len(b), len(stored), zlib.crc32(b) & 0xffffffff, data_off + len(blob)))
        blob += stored

    idx = bytearray()
    for name, rs, cs, crc, ptr in ents:
        nb = name.encode('cp1251')
        idx += struct.pack('<HIII', len(nb) + 16, rs, cs, crc) + nb + struct.pack('<I', ptr)

    with open(out, 'wb') as f:
        f.write(struct.pack('<II', 666, len(hdr)) + hdr)
        f.write(struct.pack('<II', 0, len(blob)) + blob)
        f.write(struct.pack('<II', 1, len(idx)) + idx)
    size = os.path.getsize(out)
    if not quiet or compress:
        extra = ''
        if compress:
            extra = ' (LZO1X level %d: %d of %d files compressed, file data %.1f MB -> %.1f MB)' % (
                level, n_comp, len(files), raw_total / 2**20, len(blob) / 2**20)
        print('packed', len(files), 'files,', len(dirs), 'dirs ->', out, size, 'bytes' + extra)


if __name__ == '__main__':
    main(sys.argv[1:])
