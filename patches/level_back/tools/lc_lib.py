"""Shared helpers of the level changer tools (add_level_changers.py, check_level_changers.py).

Reads the CoP (spawn version 128) all.spawn of the mod through patches/soc_levels/tools/xrspawn.py and knows the layout of one
`level_changer` packet (clone of the entities the level maker made):

  [u16 size][u16 type] section\\0 name\\0 [game id, rp] pos(3f) angles(3f) respawn... spawn id (u16) ... game vertex (u16) ... node (u32)
  ... custom data\\0 story id(u32) spawn story id(u32) [shape count u8 = 1][shape type u8 = 1 box][12 floats: 3x3 axes (diagonal = full size), offset]
  [restrictor type u8] [dest game vertex u16][dest node u32][dest position 3f][dest angles 3f] dest level\\0 dest point name\\0 [u8][u8] hint\\0 [u16]

The box is the unit cube (+-0.5) scaled by the diagonal of the 3x3 matrix, then rotated by the entity angles (xr setXYZ: yaw around y, pitch
around x, roll around z) and moved to the entity position plus the shape offset.
"""
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "patches", "soc_levels", "tools"))
import numpy as np  # noqa: E402
import xrspawn as X  # noqa: E402

SPAWN_ID_OFF = 18        # u16 spawn id inside the packet, counted from p_f (same field as strip_spawn.py)
SHAPE_RE = re.compile(rb"\xff\xff\xff\xff\xff\xff\xff\xff\x01\x01", re.S)
DEST_RE = re.compile(rb"(coop_l[0-9a-z_]+)\x00(\w+)\x00(.)(.)(level_changer_invitation)\x00(..)$", re.S)


# ---------------------------------------------------------------------------------------------- entity helpers
def entity_from_pk(eid, idhdr, pk, trailer):
    """Entity object for a finished packet (the same attribute set xrspawn.Entity computes)."""
    e = X.Entity.__new__(X.Entity)
    e.eid = eid
    e.idhdr = idhdr
    e.pk = bytearray(pk)
    e.trailer = trailer
    b = e.pk
    z = b.index(b"\0", 4)
    z2 = b.index(b"\0", z + 1)
    e.section = bytes(b[4:z]).decode("latin1")
    e.name = bytes(b[z + 1:z2]).decode("latin1")
    e.p_pos = z2 + 1 + 2
    e.p_f = e.p_pos + 24
    e.p_gv = e.p_f + 22
    e.p_lv = e.p_f + 32
    return e


def spawn_id(e):
    return struct.unpack_from("<H", e.pk, e.p_f + SPAWN_ID_OFF)[0]


def level_names(S):
    return {int(l["id"]): l["name"] for l in S.graph.levels}


def entity_level(S, e):
    return level_names(S)[int(S.graph.level_id[e.gvid])]


def nearest_vertex(S, level, pos):
    """(distance, game vertex id, local position, level vertex id) of the graph vertex of `level` nearest to pos."""
    g = S.graph
    ids = [i for i, n in level_names(S).items() if n == level]
    if not ids:
        raise SystemExit("level %s is not in the game graph" % level)
    sel = np.where(g.level_id == ids[0])[0]
    lp = g.verts["lpos"][sel].astype(np.float64)
    d = np.sqrt(((lp - np.asarray(pos, dtype=np.float64)) ** 2).sum(axis=1))
    k = int(np.argmin(d))
    v = int(sel[k])
    return float(d[k]), v, tuple(float(x) for x in g.verts["lpos"][v]), int(g.lvid[v])


def own_vertex(S, level, node):
    """(game vertex, node) of an AI node of `level`: the game vertex comes from the cross table of the level (what the level maker's own
    objects carry: gv == cross table of their node)."""
    g = S.graph
    names = [l["name"] for l in g.levels]
    xt = g.xtabs[names.index(level)]
    if node >= xt["nodes"]:
        raise SystemExit("node %d is not a node of %s (%d nodes)" % (node, level, xt["nodes"]))
    gv = int(xt["cells"][node]["v"])
    lid = [l["id"] for l in g.levels if l["name"] == level][0]
    if int(g.level_id[gv]) != lid:
        raise SystemExit("cross table of %s node %d points to a game vertex of another level" % (level, node))
    return gv, int(node)


def node_pos_hint(S, gv):
    return tuple(float(x) for x in S.graph.verts["lpos"][gv])


# ---------------------------------------------------------------------------------------------- changer packet
def parse_changer(e):
    """dict of one level changer entity (raises ValueError when the packet is not the expected layout)."""
    pk = bytes(e.pk)
    m = DEST_RE.search(pk)
    if not m:
        raise ValueError("level changer packet layout not recognised: " + e.name)
    o = m.start(1) - 30
    dgv, dnode = struct.unpack_from("<HI", pk, o)
    dpos = struct.unpack_from("<3f", pk, o + 6)
    dang = struct.unpack_from("<3f", pk, o + 18)
    ms = SHAPE_RE.search(pk, e.p_lv)
    f = struct.unpack_from("<12f", pk, ms.end())
    return dict(level=m.group(1).decode(), point=m.group(2).decode(), b1=m.group(3)[0], b2=m.group(4)[0], hint=m.group(5).decode(),
                tail=m.group(6).hex(), dgv=dgv, dnode=dnode, dpos=dpos, dang=dang, rtype=pk[o - 1], dest_off=o,
                shape=f, size=(f[0], f[4], f[8]), offset=tuple(f[9:12]), shape_off=ms.end())


def rot_matrix(ang):
    x, y, z = ang

    def ry(a):
        c, s = math.cos(a), math.sin(a)
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]

    def rx(a):
        c, s = math.cos(a), math.sin(a)
        return [[1, 0, 0], [0, c, -s], [0, s, c]]

    def rz(a):
        c, s = math.cos(a), math.sin(a)
        return [[c, -s, 0], [s, c, 0], [0, 0, 1]]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mul(mul(ry(y), rx(x)), rz(z))


def local_point(e, info, pt):
    """pt in the box frame of the changer (metres, offset removed)."""
    R = rot_matrix(e.ang)
    d = [pt[i] - e.pos[i] for i in range(3)]
    loc = [sum(R[k][i] * d[k] for k in range(3)) for i in range(3)]
    return [loc[i] - info["offset"][i] for i in range(3)]


def box_distance(e, info, pt):
    """distance (m) from pt to the box of the changer, 0 when inside."""
    loc = local_point(e, info, pt)
    half = [info["size"][i] / 2.0 for i in range(3)]
    out = [max(abs(loc[i]) - half[i], 0.0) for i in range(3)]
    return math.sqrt(sum(v * v for v in out))


def build_changer(tpl, eid, name, gvid, node, pos, ang, size, offset, dest):
    """New level changer entity cloned from the template entity `tpl`.
    dest = dict(level, gv, node, pos, ang, point)."""
    pk = bytes(tpl.pk)
    t = parse_changer(tpl)
    z = pk.index(b"\0", 4)
    z2 = pk.index(b"\0", z + 1)
    head = pk[:z + 1] + name.encode("latin1") + b"\0"
    rest = bytearray(pk[z2 + 1:])
    rest[2:14] = struct.pack("<3f", *pos)
    rest[14:26] = struct.pack("<3f", *ang)
    o = 26
    old_spawn = struct.unpack_from("<H", rest, o + SPAWN_ID_OFF)[0]
    assert old_spawn == tpl.eid, "template spawn id %d differs from its chunk id %d" % (old_spawn, tpl.eid)
    struct.pack_into("<H", rest, o + SPAWN_ID_OFF, eid)
    struct.pack_into("<H", rest, o + 22, gvid)
    struct.pack_into("<I", rest, o + 32, node)
    c0 = o + 40
    cz = rest.index(b"\0", c0)
    old_custom = bytes(rest[c0:cz])
    assert old_custom.startswith(b"[story_object]"), old_custom
    new_custom = ("[story_object]\r\nstory_id = " + name).encode("latin1")
    rest[c0:cz] = new_custom
    # shape
    ms = SHAPE_RE.search(bytes(rest), c0)
    s0 = ms.end()
    floats = [size[0], 0, 0, 0, size[1], 0, 0, 0, size[2], offset[0], offset[1], offset[2]]
    rest[s0:s0 + 48] = struct.pack("<12f", *floats)
    # destination block (found from the end of the packet, after the edits above)
    body = head + bytes(rest)
    m = DEST_RE.search(body)
    assert m, "destination block lost"
    do = m.start(1) - 30
    block = struct.pack("<HI", dest["gv"], dest["node"]) + struct.pack("<3f", *dest["pos"]) + struct.pack("<3f", *dest["ang"])
    tail = body[m.end(2) + 1:]               # [u8][u8] hint\0 [u16]
    new_body = body[:do] + block + dest["level"].encode("latin1") + b"\0" + dest["point"].encode("latin1") + b"\0" + tail
    assert t["hint"] == "level_changer_invitation"
    e = entity_from_pk(eid, tpl.idhdr, new_body, tpl.trailer)
    return e


# ---------------------------------------------------------------------------------------------- level.ai access
def extract_level_ai(addon, levels, outdir):
    """Reads level.ai of the given levels out of coop.addon (read only) into outdir/levels/<level>/level.ai. Returns the dict level -> path."""
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import xdb
    want = {("levels\\%s\\level.ai" % l).lower(): l for l in levels}
    got = {}
    members = xdb.tar_members(addon)
    with open(addon, "rb") as f:
        for name in sorted(members):
            if not name.lower().endswith((".db", ".db0", ".db1", ".db2", ".db3", ".db4", ".db5")):
                continue
            off, size = members[name]
            for ename, rs, cs, ptr in xdb.index(f, off, size):
                lvl = want.get(ename.lower())
                if lvl and rs:
                    dst = os.path.join(outdir, "levels", lvl, "level.ai")
                    if os.path.isfile(dst) and os.path.getsize(dst) == rs:
                        got[lvl] = dst
                        continue
                    f.seek(off + ptr)
                    d = f.read(cs)
                    if rs != cs:
                        d = xdb.lzo1x(d, rs)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(dst, "wb") as out:
                        out.write(d)
                    got[lvl] = dst
    return got


class AiCache:
    """level name -> X.LevelAI, from a directory with levels/<level>/level.ai (loaded on demand)."""

    def __init__(self, ai_dir):
        self.dir = ai_dir
        self.cache = {}

    def get(self, level):
        if level not in self.cache:
            p = os.path.join(self.dir, "levels", level, "level.ai")
            self.cache[level] = X.LevelAI(p) if os.path.isfile(p) else None
        return self.cache[level]


def nearest_node(ai, pt):
    """(node id, distance 3D) of the AI node nearest to pt."""
    d = (ai.x - pt[0]) ** 2 + (ai.y - pt[1]) ** 2 + (ai.z - pt[2]) ** 2
    k = int(np.argmin(d))
    return k, float(math.sqrt(d[k]))
