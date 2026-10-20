"""Appends the two Yantar military helicopters (yan_helicopt_1, yan_helicopt_3) to spawns\\all.spawn.

  python -I add_heli_spawn.py <in all.spawn> <out all.spawn>

patches/darkvalley_restore is the single owner of all.spawn: regenerate it with its tools/make_all_spawn.py, run this tool on
the result and write the output to patches/darkvalley_restore/gamedata/spawns/all.spawn. (The level.spawn of the add-on is NOT
read by the game: the server runs with spawns\\all.spawn.)

The packets are clones of the Dark Valley helicopter `val_helicopter`. Logic: configs/scripts/coop_l08_yantar/yan_helicopter_N_a.ltx.
Helicopter 1 uses the game vertex/node of the level path heli_stay_1 (1644 / 39605), helicopter 3 the nearest vertex of the level
(heli_stay_3 has no valid vertex of its own). The game graph vertex of the player decides if they go online, see NOTES.md.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "darkvalley_restore", "tools")))
import make_all_spawn as M  # noqa: E402

BS = chr(92).encode()
SPECS = [(b"yan_helicopt_1", b"yan_helicopter_1_a.ltx", (1.0, -81.0, -205.0), (1644, 39605)),
         (b"yan_helicopt_3", b"yan_helicopter_3_a.ltx", (106.0, -81.0, -207.0), None)]


def main():
    src, out = sys.argv[1], sys.argv[2]
    data = open(src, "rb").read()
    ch = dict(M.chunks(data))
    header = bytearray(ch[0])
    c1 = dict(M.chunks(ch[1]))
    ents = M.chunks(c1[1])
    count = len(ents)
    levels, verts = M.graph(ch)
    tpl = None
    for cid, pl in ents:
        d, pk, tr = M.entity_pk(pl)
        sec, nm = M.name_of(pk)
        assert nm not in (SPECS[0][0], SPECS[1][0]), "already added"
        if nm == b"val_helicopter":
            tpl = (pk, tr, cid)
    pk, tr, tcid = tpl
    body = pk[4:]
    s = body.index(b"\0")
    n = body.index(b"\0", s + 1)
    sec = body[:s]
    gid_rp = body[n + 1:n + 3]
    rest = body[n + 3:]
    oldcfg = b"scripts" + BS + b"coop_l04_darkvalley" + BS + b"val_helicopter.ltx"
    assert oldcfg in rest
    assert struct.unpack_from("<H", rest, 24 + 18)[0] == tcid
    new = []
    for k, (nm, cfg, pos, fixed) in enumerate(SPECS):
        near = M.nearest_vertex(levels, verts, "coop_l08_yantar", pos)
        gv, node = fixed if fixed else (near[1], near[3])
        print(nm, "game vertex", gv, "node", node)
        r = M.f3(*pos) + rest[12:24] + rest[24:]
        o = 24
        r = (r[:o + 18] + struct.pack("<H", count + k) + r[o + 20:o + 22] + struct.pack("<H", gv)
             + r[o + 24:o + 32] + struct.pack("<I", node) + r[o + 36:])
        r = r.replace(oldcfg, b"scripts" + BS + b"coop_l08_yantar" + BS + cfg)
        b2 = sec + b"\0" + nm + b"\0" + gid_rp + r
        pkx = struct.pack("<HH", len(b2) + 2, 1) + b2
        dx = struct.pack("<II", 0, len(pkx)) + pkx + tr
        eid = count + k
        new.append(M.chunk(eid, M.chunk(0, struct.pack("<H", eid)) + M.chunk(1, dx)))
    nn = count + len(new)
    c1n = M.chunk(0, struct.pack("<I", nn)) + M.chunk(1, c1[1] + b"".join(new)) + M.chunk(2, c1[2])
    struct.pack_into("<I", header, 36, nn)
    blob = M.chunk(0, bytes(header)) + M.chunk(1, c1n) + M.chunk(2, ch[2]) + M.chunk(3, ch[3]) + M.chunk(4, ch[4])
    with open(out, "wb") as fh:
        fh.write(blob)
    print("wrote", out, nn, "entities (was %d)" % count)


main()
