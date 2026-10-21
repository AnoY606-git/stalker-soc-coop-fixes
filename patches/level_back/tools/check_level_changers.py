"""Offline checker for the level changers of an all.spawn (no game needed).

  python check_level_changers.py <all.spawn> (--ai-dir DIR | --addon coop.addon [--cache DIR]) [--all-levels] [--quiet]

The AI node meshes (levels/<level>/level.ai) come from DIR (levels/<level>/level.ai below it) or are read out of the add-on (read only) into the
cache folder (default: a temp folder) for the levels that are needed. Without either the geometry checks that need the mesh are skipped.

Checks (exit code 1 when one FAILs):
  every changer   parses, story id == name, name unique, enabled byte set; destination level exists in the game graph; destination game vertex
                  belongs to the destination level and its level vertex / position are the arrival values written in the object; own game vertex
                  belongs to the changer's own level
  with the mesh   destination node exists and the arrival position is on it (nearest AI node within 1.6 m, 3.0 m for graph vertices placed by the
                  level maker); the changer stands on the mesh (AI nodes inside its box >= 1, nearest node of the centre within 8 m); NO arrival point of
                  any other changer lies inside this changer's box and every arrival keeps CLEAR m from the boxes of its level (a player who arrives
                  must not be thrown straight back)
  both ways       every changer X -> Y has a Y -> X changer, except the listed one-way ones (guide changers of the Cordon party vote, the exits the
                  original SoC also lacks)
  new ones        the three objects of add_level_changers.py exist, are enabled and have a way back / are the freeplay exit
"""
import argparse
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lc_lib as C  # noqa: E402
import add_level_changers as ADD  # noqa: E402
X = C.X
np = C.np

CLEAR_OLD = 2.0       # metres between an arrival point and the box of a changer of that level (old objects of the level maker)
CLEAR_NEW = 3.5       # same for the objects of this patch
NODE_TOL = 1.6        # arrival position vs nearest AI node (graph vertices are on nodes)
STAND_TOL = 8.0

# Exits that have no way back on purpose. key = changer name.
ONE_WAY = {
    "val_esc_level_changer": "Cordon is left through the guide; the original SoC has exit_to_darkvalley only from Dark Valley",
    "aes_1_level_changer": "NPP chain (Stancia -> Sarcophagus): the original SoC has no way back",
    "sar_level_changer": "NPP chain (Sarcophagus -> Control Monolith): the original SoC has no way back",
    "con_level_changer": "NPP chain (Control Monolith -> CNPP-2): the original SoC has no way back",
    "pri_level_changer": "NPP chain (Pripyat -> Stancia): the original SoC has no exit from Stancia to Pripyat",
    "aes_2_esc_freeplay_level_changer": "freeplay exit: scripted, one way by design",
}


def is_guide(name):
    return "_guide_level_changer" in name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spawn")
    ap.add_argument("--ai-dir")
    ap.add_argument("--addon")
    ap.add_argument("--cache")
    ap.add_argument("--all-levels", action="store_true", help="load the mesh of every level with a changer (slow, a lot of memory)")
    ap.add_argument("--quiet", action="store_true", help="print FAIL and summary lines only")
    a = ap.parse_args()

    S = X.AllSpawn(open(a.spawn, "rb").read())
    g = S.graph
    lv = C.level_names(S)
    lcs = [e for e in S.ents if e.section == "level_changer"]
    info = {e.name: C.parse_changer(e) for e in lcs}
    by_name = {e.name: e for e in lcs}
    own = {e.name: lv[int(g.level_id[e.gvid])] for e in lcs}
    fails = []
    notes = []

    def ok(msg):
        if not a.quiet:
            print("PASS " + msg)

    def bad(msg):
        fails.append(msg)
        print("FAIL " + msg)

    def warn(msg):
        notes.append(msg)
        if not a.quiet:
            print("NOTE " + msg)

    print("%s: %d entities, %d level changers" % (a.spawn, len(S.ents), len(lcs)))

    # ---- basic
    names = [e.name for e in lcs]
    if len(set(names)) == len(names):
        ok("changer names are unique")
    else:
        bad("duplicate changer names")
    for e in lcs:
        t = info[e.name]
        cd = e.custom().replace("\r\n", "\n")
        if "story_id = " + e.name not in cd:
            (bad if e.name in ADD.NAMES else warn)("%s: story id in the custom data is not its name (%r)" % (e.name, cd))
        if t["b1"] != 1:
            bad("%s: enabled byte is %d" % (e.name, t["b1"]))
        if t["level"] not in lv.values():
            bad("%s: destination level %s is not in the game graph" % (e.name, t["level"]))
            continue
        dl = lv[int(g.level_id[t["dgv"]])] if t["dgv"] < g.vc else None
        if dl != t["level"]:
            bad("%s: destination game vertex %d is on %s, not on %s" % (e.name, t["dgv"], dl, t["level"]))
            continue
        if int(g.lvid[t["dgv"]]) != t["dnode"]:
            bad("%s: destination node %d differs from the level vertex %d of the destination game vertex" % (e.name, t["dnode"], int(g.lvid[t["dgv"]])))
        lp = g.verts["lpos"][t["dgv"]]
        if max(abs(float(lp[i]) - t["dpos"][i]) for i in range(3)) > 0.01:
            bad("%s: destination position differs from the position of the destination game vertex" % e.name)
        if own[e.name] != lv[int(g.level_id[e.gvid])]:
            bad("%s: own game vertex is on another level" % e.name)
        names_l = [l["name"] for l in g.levels]
        xt = g.xtabs[names_l.index(own[e.name])]
        if e.lvid >= xt["nodes"] or int(xt["cells"][e.lvid]["v"]) != e.gvid:
            bad("%s: own game vertex %d is not the cross table game vertex of its own node %d" % (e.name, e.gvid, e.lvid))
    ok("destinations: %d changers checked (level, game vertex, node, position)" % len(lcs))

    # ---- new objects exist
    for n in ADD.NAMES:
        if n in by_name:
            ok("new changer %s is in the file, level %s -> %s, enabled byte %d" % (n, own[n], info[n]["level"], info[n]["b1"]))
        else:
            bad("new changer %s is MISSING (run add_level_changers.py)" % n)

    # ---- both directions
    pairs = {(own[n], info[n]["level"]) for n in names}
    for n in names:
        if is_guide(n) or n in ONE_WAY:
            continue
        x, y = own[n], info[n]["level"]
        if (y, x) not in pairs:
            bad("%s: %s -> %s has no changer back" % (n, x, y))
    ok("every walking exit has a way back (guide changers and %d listed one-way exits excepted)" % len(ONE_WAY))
    for n in ("rad_mil_level_changer", "pri_rad_level_changer"):
        if n in by_name:
            x, y = own[n], info[n]["level"]
            fwd = [m for m in names if own[m] == y and info[m]["level"] == x and not is_guide(m)]
            if fwd:
                ok("both directions %s <-> %s: %s and %s" % (x, y, n, ", ".join(fwd)))
            else:
                bad("%s has no partner %s -> %s" % (n, y, x))

    # ---- mesh
    ai_dir = a.ai_dir
    if ai_dir is None and a.addon:
        ai_dir = a.cache or os.path.join(tempfile.gettempdir(), "lc_check_ai")
        need = set()
        for n in names:
            if a.all_levels or n in ADD.NAMES or info[n]["level"] in {c["dest_level"] for c in ADD.CHANGERS} or own[n] in {c["level"] for c in ADD.CHANGERS}:
                need.add(own[n])
                need.add(info[n]["level"])
        need = sorted(need)
        print("reading level.ai of %d levels from the add-on into %s" % (len(need), ai_dir))
        C.extract_level_ai(a.addon, need, ai_dir)
    if ai_dir is None:
        print("no --ai-dir / --addon: mesh checks skipped")
    else:
        cache = C.AiCache(ai_dir)
        focus = set()
        for n in names:
            if a.all_levels or n in ADD.NAMES:
                focus.add(n)
        for c in ADD.CHANGERS:   # also the old objects around the new ones (same levels)
            for n in names:
                if own[n] in (c["level"], c["dest_level"]) or info[n]["level"] in (c["level"], c["dest_level"]):
                    focus.add(n)
        for n in sorted(focus):
            e, t = by_name[n], info[n]
            new = n in ADD.NAMES
            ai_dst = cache.get(t["level"])
            ai_own = cache.get(own[n])
            if ai_dst is None or ai_own is None:
                warn("%s: no level.ai for %s or %s, mesh checks skipped" % (n, own[n], t["level"]))
                continue
            # arrival on the mesh
            if t["dnode"] < ai_dst.count:
                node, d = C.nearest_node(ai_dst, t["dpos"])
                px, py, pz = ai_dst.x[t["dnode"]], ai_dst.y[t["dnode"]], ai_dst.z[t["dnode"]]
                dn = ((px - t["dpos"][0]) ** 2 + (py - t["dpos"][1]) ** 2 + (pz - t["dpos"][2]) ** 2) ** 0.5
                if dn <= (NODE_TOL if new else 3.0):
                    ok("%s: arrival node %d exists on %s and is %.2f m from the arrival position (nearest node %d, %.2f m)" % (n, t["dnode"], t["level"], dn, node, d))
                else:
                    bad("%s: arrival node %d is %.1f m from the arrival position on %s" % (n, t["dnode"], dn, t["level"]))
            else:
                bad("%s: arrival node %d does not exist on %s (%d nodes)" % (n, t["dnode"], t["level"], ai_dst.count))
            # standing on the mesh
            node, d = C.nearest_node(ai_own, e.pos)
            if d <= STAND_TOL:
                ok("%s: stands on the mesh of %s (nearest node %.1f m)" % (n, own[n], d))
            else:
                (bad if new else warn)("%s: nearest AI node of %s is %.1f m away" % (n, own[n], d))
            if e.lvid < ai_own.count:
                dn = ((ai_own.x[e.lvid] - e.pos[0]) ** 2 + (ai_own.y[e.lvid] - e.pos[1]) ** 2 + (ai_own.z[e.lvid] - e.pos[2]) ** 2) ** 0.5
                if dn <= 3.0:
                    ok("%s: its own node %d is %.2f m from its position" % (n, e.lvid, dn))
                else:
                    (bad if new else warn)("%s: its own node %d is %.1f m from its position" % (n, e.lvid, dn))
            else:
                bad("%s: its own node %d does not exist on %s" % (n, e.lvid, own[n]))
            # nodes inside the box
            R = C.rot_matrix(e.ang)
            half = [t["size"][i] / 2.0 for i in range(3)]
            pts = np.column_stack([ai_own.x - e.pos[0], ai_own.y - e.pos[1], ai_own.z - e.pos[2]])
            near = np.abs(pts).max(axis=1) < max(half) * 2 + 30
            sel = np.where(near)[0]
            Rm = np.array(R)
            loc = pts[sel] @ Rm - np.array(t["offset"])
            inside = (np.abs(loc[:, 0]) <= half[0]) & (np.abs(loc[:, 1]) <= half[1]) & (np.abs(loc[:, 2]) <= half[2])
            cnt = int(inside.sum())
            if cnt >= 1:
                ok("%s: %d AI nodes of %s inside its box (it can be reached on the mesh)" % (n, cnt, own[n]))
            else:
                (bad if new else warn)("%s: no AI node inside its box on %s" % (n, own[n]))
            # arrival vs boxes of the destination level
            worst = None
            for m in names:
                if own[m] != t["level"]:
                    continue
                dist = C.box_distance(by_name[m], info[m], t["dpos"])
                if worst is None or dist < worst[0]:
                    worst = (dist, m)
            if worst is None:
                continue
            need = CLEAR_NEW if new else CLEAR_OLD
            if worst[0] <= 0.0:
                bad("%s: the arrival point lies INSIDE the box of %s (a player would be sent straight back)" % (n, worst[1]))
            elif worst[0] < need:
                (bad if new else warn)("%s: the arrival point is only %.1f m from the box of %s (want %.1f)" % (n, worst[0], worst[1], need))
            else:
                ok("%s: arrival point keeps %.1f m from the nearest changer box on %s (%s)" % (n, worst[0], t["level"], worst[1]))
        # the new ones must also keep clear of each other's arrivals on their own level (covered above); the freeplay exit must be far from routes
        if "aes_2_esc_freeplay_level_changer" in by_name:
            e = by_name["aes_2_esc_freeplay_level_changer"]
            gate = by_name.get("con_level_changer")
            if gate is not None:
                d = C.math.dist(e.pos, info["con_level_changer"]["dpos"])
                if d > 300.0:
                    ok("freeplay exit is %.0f m from the arrival of the Control Monolith exit (nobody walks into it by accident)" % d)
                else:
                    bad("freeplay exit is only %.0f m from the arrival point of the Control Monolith exit" % d)

    print("%d FAIL, %d NOTE" % (len(fails), len(notes)))
    if not fails:
        print("LEVEL CHANGERS OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
