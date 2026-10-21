"""Adds the missing way back (and the freeplay exit) as level changers to an all.spawn.

  python add_level_changers.py <all.spawn> [<all.spawn> ...]      add what is missing, rewrite in place (atomic, refuses when the file changed meanwhile)
  python add_level_changers.py --check <all.spawn> [...]          only list, exit 1 when any of them is missing
  python add_level_changers.py --report <all.spawn>               print the three objects as they are (or would be) written

The three objects (all values in CHANGERS below):
  rad_mil_level_changer            Radar -> Army Warehouses. SoC `l10_radar exit_to_military_01` (same position, angles and size as the
                                   original), arrival on the Army Warehouses graph vertex next to the "no" point of the old question.
  pri_rad_level_changer            Pripyat -> Radar. SoC `l11_pripyat exit_to_radar_01` (a 259 m wide wall on the south edge of the map). The
                                   mod's arrival from the Radar (rad_pri_lc_graph_point, 26.6 -2.2 -296.8) lies INSIDE that wall, so the box is
                                   moved 7 m south and narrowed to the walkable width (62 x 15 x 2 m at z -304.5); the arrival is 6.7 m in front.
  aes_2_esc_freeplay_level_changer CNPP-2 -> Cordon rookie village, used only by the freeplay script (patches/freeplay): the script teleports
                                   the party into it after the true ending. It stands in the far south east corner of the level, far from any
                                   route, and the script keeps it closed (enable_level_changer(false)) until the freeplay starts.

Pipeline: this is one more in-place step on the shared all.spawn (same pattern as no_tech_parts/tools/strip_spawn.py and
bar_arrival_anomalies/tools/strip_bar_anomalies.py). It selects by NAME, never by id, appends the new entities with the next free ids (chunk id ==
spawn id in the packet, as everywhere in this file), is idempotent (a second run finds all three and writes nothing) and can run before or after
the strip steps (they renumber the ids contiguously and keep the new ones). Order after a regeneration:
  darkvalley_restore/tools/make_all_spawn.py -> cordon_bridge/tools/make_paths.py -> no_tech_parts/tools/strip_spawn.py
  -> bar_arrival_anomalies/tools/strip_bar_anomalies.py -> this tool.
Needs patches/soc_levels/tools/xrspawn.py (round trip of an untouched file is byte identical).
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lc_lib as C  # noqa: E402
X = C.X

# destination points are given as a reference position; the nearest game graph vertex of the destination level is used at build time
# (the arrival is that vertex exactly, like every other changer of the file).
CHANGERS = [
    dict(name="rad_mil_level_changer", template="mil_rad_level_changer", level="coop_l09_radar",
         pos=(562.4259033203125, -53.76308822631836, -421.7624206542969), ang=(0.06606201082468033, -0.37350863218307495, 0.052097685635089874),
         size=(11.3, 11.38, 1.6), offset=(0.0, 0.0, -0.9), node=196397,
         dest_level="coop_l07_military", dest_ref=(52.6, -18.4, 361.6), dest_yaw=-2.62, dest_point="rad_mil_lc_graph_point"),
    dict(name="pri_rad_level_changer", template="mil_rad_level_changer", level="coop_l10_pripyat",
         pos=(14.0, -2.4, -304.5), ang=(0.0, 0.0, 0.0),
         size=(62.0, 15.0, 2.0), offset=(0.0, 0.0, 0.0), node=121680,
         dest_level="coop_l09_radar", dest_ref=(384.0, -34.0, 141.9), dest_yaw=3.04, dest_point="pri_rad_lc_graph_point"),
    dict(name="aes_2_esc_freeplay_level_changer", template="mil_rad_level_changer", level="coop_l11_stancia_2",
         pos=(981.7, 0.0, 337.7), ang=(0.0, 0.0, 0.0),
         size=(6.0, 8.0, 6.0), offset=(0.0, 0.0, 0.0), node=259834,
         dest_level="coop_l01_escape", dest_ref=(-199.0, -19.9, -140.6), dest_yaw=-1.507, dest_point="aes_2_esc_lc_graph_point"),
]
NAMES = [c["name"] for c in CHANGERS]


def plan(S):
    """list of (spec, entity) for the changers that are not in S yet (entities built with ids len(S.ents), +1, ...)."""
    have = {e.name for e in S.ents}
    tpl = {}
    for e in S.ents:
        if e.section == "level_changer":
            tpl[e.name] = e
    out = []
    eid = len(S.ents)
    for c in CHANGERS:
        if c["name"] in have:
            continue
        t = tpl.get(c["template"])
        if t is None:
            raise SystemExit("template level changer %s is not in the file" % c["template"])
        dd, dgv, dpos, dnode = C.nearest_vertex(S, c["dest_level"], c["dest_ref"])
        if dd > 2.0:
            raise SystemExit("%s: no graph vertex of %s within 2 m of %s (nearest %.1f m)" % (c["name"], c["dest_level"], c["dest_ref"], dd))
        egv, enode = C.own_vertex(S, c["level"], c["node"])
        ed = math.dist(c["pos"], C.node_pos_hint(S, egv))
        dest = dict(level=c["dest_level"], gv=dgv, node=dnode, pos=dpos, ang=(0.0, c["dest_yaw"], 0.0), point=c["dest_point"])
        e = C.build_changer(t, eid, c["name"], egv, enode, c["pos"], c["ang"], c["size"], c["offset"], dest)
        out.append((c, e, dict(dest_gv=dgv, dest_node=dnode, dest_pos=dpos, own_gv=egv, own_node=enode, own_dist=ed)))
        eid += 1
    return out


def describe(c, e, extra):
    return ("%s: level %s at (%.1f, %.1f, %.1f) size %.2f x %.2f x %.2f, own graph vertex %d node %d (%.1f m away) -> %s graph vertex %d node %d at (%.1f, %.1f, %.1f), yaw %.2f"
            % (c["name"], c["level"], c["pos"][0], c["pos"][1], c["pos"][2], c["size"][0], c["size"][1], c["size"][2], extra["own_gv"], extra["own_node"],
               extra["own_dist"], c["dest_level"], extra["dest_gv"], extra["dest_node"], extra["dest_pos"][0], extra["dest_pos"][1], extra["dest_pos"][2], c["dest_yaw"]))


def process(path, check, report):
    st = os.stat(path)
    raw = open(path, "rb").read()
    S = X.AllSpawn(raw)
    names = {e.name for e in S.ents}
    todo = plan(S)
    print("%s: %d entities, %d of %d changers present" % (path, len(S.ents), len(NAMES) - len(todo), len(NAMES)))
    if report:
        for c in CHANGERS:
            if c["name"] in names:
                print("  present: " + c["name"])
        for c, e, extra in todo:
            print("  would add: " + describe(c, e, extra))
        return len(todo)
    if check:
        for c, e, extra in todo:
            print("  missing: " + c["name"])
        return len(todo)
    if not todo:
        return 0
    for e in S.ents:
        assert C.spawn_id(e) == e.eid, "packet spawn id differs from the chunk id: %s %s" % (e.section, e.name)
    for c, e, extra in todo:
        S.ents.append(e)
        print("  add: " + describe(c, e, extra))
    out = S.pack()
    chk = X.AllSpawn(out)
    assert len(chk.ents) == len(S.ents)
    assert all(x.eid == i and C.spawn_id(x) == i for i, x in enumerate(chk.ents))
    for c, e, extra in todo:
        back = [x for x in chk.ents if x.name == c["name"]]
        assert len(back) == 1
        info = C.parse_changer(back[0])
        assert info["level"] == c["dest_level"] and info["dgv"] == extra["dest_gv"] and info["dnode"] == extra["dest_node"], c["name"]
        assert back[0].gvid == extra["own_gv"] and back[0].lvid == extra["own_node"], c["name"]
        assert info["b1"] == 1 and info["b2"] == 1
    st2 = os.stat(path)
    if (st2.st_mtime_ns, st2.st_size) != (st.st_mtime_ns, st.st_size):
        sys.exit("%s changed while it was processed, nothing written" % path)
    tmp = path + ".tmp_lc"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)
    print("  written: %d entities, %d bytes" % (len(chk.ents), len(out)))
    return 0


def main():
    args = sys.argv[1:]
    check = "--check" in args
    report = "--report" in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        sys.exit(__doc__)
    left = sum(process(p, check, report) for p in files)
    sys.exit(1 if (check and left) else 0)


if __name__ == "__main__":
    main()
