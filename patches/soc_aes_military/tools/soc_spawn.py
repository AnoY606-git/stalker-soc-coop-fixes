"""Minimal reader of the Steam SoC level.spawn (version 118: one chunk per entity, no sub chunks) for check_military_chain.py --verify-zones.
load(path) -> list of dict(section, name, pos, angles, cd (custom data), pl (raw packet), ce (offset of the end of the custom data))
shapes_of(entity) -> [('sph', centre, radius) | ('box', 12 floats: 3x3 matrix (diagonal = full size) and the offset)]
Needs patches\\soc_levels\\tools\\xrspawn.py for the chunk walker only."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'soc_levels', 'tools'))
import xrspawn as X  # noqa: E402


def shapes_of(r):
    pl = r['pl']
    o = r['ce'] + 1 + 8
    try:
        n = pl[o]
        o += 1
        out = []
        for _ in range(n):
            t = pl[o]
            o += 1
            if t == 0:
                c = struct.unpack_from('<3f', pl, o)
                rad = struct.unpack_from('<f', pl, o + 12)[0]
                o += 16
                out.append(('sph', [round(v, 1) for v in c], round(rad, 1)))
            else:
                m = struct.unpack_from('<12f', pl, o)
                o += 48
                out.append(('box', [round(v, 1) for v in m]))
        return out
    except Exception:
        return None


def load(path):
    res = []
    for cid, pl in X.chunks(open(path, 'rb').read()):
        z = pl.index(b'\0', 2)
        z2 = pl.index(b'\0', z + 1)
        sec = pl[2:z].decode('latin1')
        name = pl[z + 1:z2].decode('latin1')
        p = z2 + 3
        pos = struct.unpack_from('<3f', pl, p)
        ang = struct.unpack_from('<3f', pl, p + 12)
        pf = p + 24
        try:
            co = pf + 38
            ce = pl.index(b'\0', co)
            cd = pl[co:ce].decode('cp1251', 'replace')
        except Exception:
            ce = 0
            cd = ''
        res.append(dict(cid=cid, section=sec, name=name, pos=pos, angles=ang, cd=cd, pl=pl, ce=ce))
    return res
