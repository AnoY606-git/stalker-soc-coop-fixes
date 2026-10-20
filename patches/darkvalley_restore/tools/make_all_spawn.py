"""Adds two objects of the original SoC to spawns\\all.spawn of Shadow of COOP 8.0.

  python make_all_spawn.py <path to coop.addon> <out all.spawn>

Run from anywhere. The output goes to patches/darkvalley_restore/gamedata/spawns/all.spawn (see NOTES.md).
Needs ../../../tools/xdb.py (read-only access to the addon; the addon is never modified).

Objects (all values come from the original SoC all.spawn dump of the levels, position/shape/direction unchanged):
  1. coop_l04_darkvalley  level_changer  val_esc_level_changer   (SoC exit_to_escape, south gate -> Cordon start_actor_02)
  2. coop_l01_escape      space_restrictor esc_return_from_dv     (SoC esc_return_from_dv, arrival zone from Dark Valley)
The destination ids (game vertex, level vertex) are taken from the game graph that is stored in the same file.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "tools")))
import xdb  # noqa: E402


def read_all_spawn(addon):
    members = xdb.tar_members(addon)
    found = None
    with open(addon, "rb") as f:
        for name in sorted(members):
            if not name.lower().endswith((".db", ".db0", ".db1", ".db2", ".db3", ".db4", ".db5")):
                continue
            off, size = members[name]
            for ename, rs, cs, ptr in xdb.index(f, off, size):
                if ename.lower() == "spawns\\all.spawn" and rs:
                    found = (off, rs, cs, ptr)
        off, rs, cs, ptr = found
        f.seek(off + ptr)
        data = f.read(cs)
        if rs != cs:
            data = xdb.lzo1x(data, rs)
    return data


def chunks(b):
    i, out = 0, []
    while i < len(b):
        cid, sz = struct.unpack_from("<II", b, i)
        out.append((cid, b[i + 8:i + 8 + sz]))
        i += 8 + sz
    return out


def chunk(cid, data):
    return struct.pack("<II", cid, len(data)) + data


def entity_pk(payload):
    """payload of one spawn graph vertex -> (data of its chunk 1, packet bytes incl. its u16 size, trailer)"""
    c0 = struct.unpack_from("<I", payload, 4)[0]
    p1 = 8 + c0
    sz = struct.unpack_from("<I", payload, p1 + 4)[0]
    data = payload[p1 + 8:p1 + 8 + sz]
    psz = struct.unpack_from("<I", data, 4)[0]
    return data, data[8:8 + psz], data[8 + psz:]


def name_of(pk):
    z = pk.index(b"\0", 4)
    z2 = pk.index(b"\0", z + 1)
    return pk[4:z], pk[z + 1:z2]


def graph(all_spawn_chunks):
    g = all_spawn_chunks[4]
    ver, vc, ec, dpc = struct.unpack_from("<BHII", g, 0)
    p = 11 + 16
    lc = g[p]
    p += 1
    levels = {}
    for _ in range(lc):
        z = g.index(b"\0", p)
        name = g[p:z].decode()
        p = z + 1 + 12
        lid = g[p]
        p += 1
        z = g.index(b"\0", p)
        p = z + 1 + 16
        levels[lid] = name
    verts = []
    for _ in range(vc):
        lp = struct.unpack_from("<3f", g, p)
        lw, = struct.unpack_from("<I", g, p + 24)
        verts.append((lp, lw & 0xff, lw >> 8))
        p += 42
    return levels, verts


def nearest_vertex(levels, verts, level, pos):
    best = None
    for i, (lp, lid, node) in enumerate(verts):
        if levels[lid] != level:
            continue
        d = math.dist(lp, pos)
        if best is None or d < best[0]:
            best = (d, i, lp, node)
    return best


def f3(*v):
    return struct.pack("<3f", *v)


def build_packet(tpl_pk, tpl_cid, new_cid, new_gv, new_node, new_name, pos, ang, old_custom, new_custom, shape12, tail_edit):
    """Clone a template packet. shape12 = 12 floats of a box (axis_x, axis_y, axis_z, offset)."""
    body = tpl_pk[4:]                       # after u16 size + u16 type
    sec_end = body.index(b"\0")
    sec = body[:sec_end]
    name_end = body.index(b"\0", sec_end + 1)
    old_name = body[sec_end + 1:name_end]
    rest = body[name_end + 1:]
    gid_rp = rest[:2]
    rest = rest[2:]
    rest = f3(*pos) + f3(*ang) + rest[24:]
    # after pos/angle: respawn, id, parent, phantom, flags, version, 3 x u16, spawn_id, u16, game_vertex_id, distance f32, direct_control u32, node u32
    o = 24
    assert struct.unpack_from("<H", rest, o + 18)[0] == tpl_cid, "spawn id of the template not where expected"
    rest = (rest[:o + 18] + struct.pack("<H", new_cid) + rest[o + 20:o + 22] + struct.pack("<H", new_gv)
            + rest[o + 24:o + 32] + struct.pack("<I", new_node) + rest[o + 36:])
    if old_custom not in rest:
        raise SystemExit("template custom_data not found")
    i = rest.index(old_custom)
    head, after = rest[:i], rest[i + len(old_custom):]
    # after: <0> ffffffff ffffffff <shape count u8> <shape type u8> <shape data> <restrictor type u8> <dest part ...>
    assert after[:1] == b"\0" and after[1:9] == b"\xff" * 8, after[:12].hex()
    cnt, typ = after[9], after[10]
    assert cnt == 1
    if typ == 0:                            # sphere: 4 floats
        shape_len = 16
    elif typ == 1:                          # box: 12 floats
        shape_len = 48
    else:
        raise SystemExit("unknown shape type")
    tail = after[11 + shape_len:]
    new_after = after[:9] + b"\x01\x01" + struct.pack("<12f", *shape12) + tail
    body2 = sec + b"\0" + new_name + b"\0" + gid_rp + head + new_custom + new_after
    body2 = tail_edit(body2) if tail_edit else body2
    pk = struct.pack("<HH", len(body2) + 2, 1) + body2
    return pk, sec, old_name


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    addon, out = sys.argv[1], sys.argv[2]
    data = read_all_spawn(addon)
    ch = dict(chunks(data))
    header = bytearray(ch[0])
    c1 = dict(chunks(ch[1]))
    ents = chunks(c1[1])
    count = len(ents)
    assert struct.unpack_from("<I", c1[0], 0)[0] == count, "entity count mismatch"
    levels, verts = graph(ch)

    tpl = {}
    for cid, pl in ents:
        d, pk, tr = entity_pk(pl)
        sec, nm = name_of(pk)
        if nm in (b"val_x18_level_changer", b"esc_smart_terrain_1_stalker_guide_space_restrictor"):
            tpl[nm] = (d, pk, tr, pl, cid)
        assert nm not in (b"val_esc_level_changer", b"esc_return_from_dv"), "already patched"

    # ---- 1. DV level changer to Cordon
    d, pk, tr, pl, tcid1 = tpl[b"val_x18_level_changer"]
    dest = nearest_vertex(levels, verts, "coop_l01_escape", (345.363067626953, 15.0583877563477, -26.5997104644775))
    dist, gvid, dpos, node = dest
    print("destination vertex", gvid, "node", node, "at", dpos, "(%.2f m from the SoC point)" % dist)
    ddir = (0.0075098886154592, 1.03138911724091, -0.000671439804136753)

    def edit_changer(body):
        # restrictor type u8, then dest u16 gvid, u32 node, 3f pos, 3f dir, 2 strings
        marker = b"coop_l04_x18\0val_x18_lc_graph_point\0"
        j = body.index(marker)
        pre = body[:j - 2 - 4 - 12 - 12]
        post = body[j + len(marker):]
        return (pre + struct.pack("<HI", gvid, node) + f3(*dpos) + f3(*ddir)
                + b"coop_l01_escape\0val_esc_lc_graph_point\0" + post)

    pos1 = (-44.6241874694824, 0.434771537780762, -548.773376464844)
    ang1 = (-0.0555085316300392, 1.58861577510834, -0.046546284109354)
    shape1 = (4.62548828125, 0, 0, 0, 17.6304035186768, 0, 0, 0, 11.13463306427, 0, 0, 0)
    gv1 = nearest_vertex(levels, verts, "coop_l04_darkvalley", pos1)
    pk1, _, _ = build_packet(pk, tcid1, count, gv1[1], gv1[3], b"val_esc_level_changer", pos1, ang1,
                             b"[story_object]\r\nstory_id = val_x18_level_changer",
                             b"[story_object]\r\nstory_id = val_esc_level_changer", shape1, edit_changer)

    # ---- 2. Cordon arrival zone
    d2, pk2t, tr2, pl2, tcid2 = tpl[b"esc_smart_terrain_1_stalker_guide_space_restrictor"]
    old_cd = b"[logic]\r\ncfg = scripts\\coop_l01_escape\\space_restrictors\\esc_smart_terrain_1_stalker_guide_space_restrictor.ltx"
    new_cd = b"[logic]\r\ncfg = scripts\\coop_l01_escape\\space_restrictors\\esc_return_from_dv.ltx"
    pos2 = (304.257751464844, 15.7128829956055, 5.41214895248413)
    ang2 = (-0.0412506200373173, 0.922310173511505, 0.043754868209362)
    shape2 = (31.6230964660645, 0, 0, 0, 23.3236026763916, 0, 0, 0, 18.1159687042236, 0, 0, 0)
    gv2 = nearest_vertex(levels, verts, "coop_l01_escape", pos2)
    pk2, _, _ = build_packet(pk2t, tcid2, count + 1, gv2[1], gv2[3], b"esc_return_from_dv", pos2, ang2, old_cd, new_cd, shape2, None)
    print("graph vertex of the changer", gv1[1], "node", gv1[3], "| of the Cordon zone", gv2[1], "node", gv2[3])

    new_ents = []
    for k, (pkx, trx) in enumerate(((pk1, tr), (pk2, tr2))):
        eid = count + k
        data_x = struct.pack("<II", 0, len(pkx)) + pkx + trx
        payload = chunk(0, struct.pack("<H", eid)) + chunk(1, data_x)
        new_ents.append(chunk(eid, payload))

    sub1 = c1[1] + b"".join(new_ents)
    n = count + len(new_ents)
    c1_new = chunk(0, struct.pack("<I", n)) + chunk(1, sub1) + chunk(2, c1[2])
    struct.pack_into("<I", header, 36, n)
    assert struct.unpack_from("<I", ch[0], 36)[0] == count
    blob = chunk(0, bytes(header)) + chunk(1, c1_new) + chunk(2, ch[2]) + chunk(3, ch[3]) + chunk(4, ch[4])
    with open(out, "wb") as fh:
        fh.write(blob)
    print("wrote", out, len(blob), "bytes,", n, "entities (was %d)" % count)


if __name__ == "__main__":
    main()
