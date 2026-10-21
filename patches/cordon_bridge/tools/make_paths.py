"""Moves the Cordon bridge soldiers to the Shadow of Chernobyl posts: rewrites the patrol paths of esc_smart_terrain_7 in all.spawn.

  python make_paths.py <in all.spawn> <out all.spawn> --ai <Cordon level.ai>             write
  python make_paths.py <in all.spawn> -               --ai <Cordon level.ai> --check      print the plan, validate <in>, write nothing
  python make_paths.py <patched all.spawn> -          --ai <Cordon level.ai> --verify <original all.spawn>

Only chunk 3 (patrol paths) of the spawn file is rebuilt, every other chunk is copied byte for byte. Paths whose name is not in
POSTS are written back unchanged (the round trip of the whole chunk is verified). Level vertex ids come from the nearest AI node,
game vertex ids from the level cross table, so both are valid for the level. Idempotent: running it on its own output changes nothing.

--check   prints the plan and validates <in> (every point of every esc_smart_terrain_7_walker* path: level vertex id on the AI mesh,
          game vertex id = cross table entry of that node, game vertex on the Cordon level). Exit code 1 on any problem.
--verify  compares a patched file with the original: chunks 0, 1, 2 and 4 byte for byte, chunk 3 path by path (only the POSTS paths may
          differ or be new, all others byte for byte), then runs the --check validation on the patched file.

Posts (SoC esc_bridge posts, the Steam SoC all.spawn, same Cordon coordinates as the mod):
  army_1  post1  walk (45.5, 2.7, 142.0)   look (54.4, -0.7, 114.8)
  army_2  post3  walk (63.0, 3.2, 171.7)   look (82.6, 12.7, 170.2)
  army_3  post4  walk (47.8, 2.7, 174.2)   look (29.2, 11.1, 168.7)
  army_4  post5  patrol (71.5, 2.8, 135.7) <-> (70.9, 2.8, 168.4)   look (73.7, 2.7, 124.8) / (69.2, 2.8, 186.6)
  army_5  post6  walk (51.4, 2.3, 178.9)   look (46.0, 4.2, 190.1)         (new path)
  Kuznetsov (post2) keeps his old path: it is 5 m from the SoC post2.
Before this change all four soldiers stood on the railway bridge deck (y about 20), 17 m above the SoC posts.
The restrictor esc_the_order_to_attack_the_players_space_restrictor (box 32.3 x 35.6 x 42.4 m around 56.9 0.6 157.1, y -17.2 .. 18.4) is
NOT changed: the soldiers no longer stand on the deck, so there is no reason to move it.
"""
import argparse
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "soc_levels", "tools"))
import xrspawn as X  # noqa: E402

POSTS = {
    # path name: [(point name, (x, y, z), flag bit)]
    "esc_smart_terrain_7_walker_1_walk": [("name00", (45.5, 2.7, 142.0), 1)],
    "esc_smart_terrain_7_walker_1_look": [("name00", (54.4, -0.7, 114.8), 1)],
    "esc_smart_terrain_7_walker_2_walk": [("name00", (63.0, 3.2, 171.7), 1)],
    "esc_smart_terrain_7_walker_2_look": [("name00", (82.6, 12.7, 170.2), 1)],
    "esc_smart_terrain_7_walker_3_walk": [("name00", (47.8, 2.7, 174.2), 1)],
    "esc_smart_terrain_7_walker_3_look": [("name00", (29.2, 11.1, 168.7), 1)],
    "esc_smart_terrain_7_walker_4_walk": [("name00|t=5000", (71.5, 2.8, 135.7), 1), ("name01|t=5000", (70.9, 2.8, 168.4), 2)],
    "esc_smart_terrain_7_walker_4_look": [("name00", (73.7, 2.7, 124.8), 1), ("name01", (69.2, 2.8, 186.6), 2)],
    "esc_smart_terrain_7_walker_5_walk": [("name00", (51.4, 2.3, 178.9), 1)],
    "esc_smart_terrain_7_walker_5_look": [("name00", (46.0, 4.2, 190.1), 1)],
}
# edge table of a 2 point path: 0 -> 1 and 1 -> 0 (copied from the existing 2 point paths of the mod)
EDGES2 = bytes.fromhex("0000000001000000010000000000803f0100000001000000000000000000803f")
PREFIX = "esc_smart_terrain_7_walker"

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst", help="output file, or - with --check / --verify")
ap.add_argument("--ai", required=True)
ap.add_argument("--check", action="store_true", help="print the plan, validate <in>, write nothing")
ap.add_argument("--verify", metavar="ORIGINAL", help="compare <in> (the patched file) with the original all.spawn")
a = ap.parse_args()

raw = open(a.src, "rb").read()
top = X.chunks(raw)
assert [c for c, _ in top] == [0, 1, 2, 3, 4], [c for c, _ in top]
P = X.Patrols(dict(top)[3])
assert P.pack() == dict(top)[3], "patrol chunk does not round trip"
G = X.GameGraph(dict(top)[4])
ai = X.LevelAI(a.ai)
cross = G.xtabs[0]["cells"]["v"]
assert G.levels[0]["name"] == "coop_l01_escape"
CORDON_ID = G.levels[0]["id"]
LEVEL_ID = G.level_id


def node(pt):
    dx = ai.x - pt[0]
    dz = ai.z - pt[2]
    dy = (ai.y - pt[1]) * 2.0
    d2 = dx * dx + dz * dz + dy * dy
    i = int(np.argmin(d2))
    return i, (float(ai.x[i]), float(ai.y[i]), float(ai.z[i]))


def validate(paths, label):
    """every point of every bridge path: AI node exists, game vertex = cross table entry, game vertex on the Cordon level."""
    bad = 0
    n = 0
    for p in paths:
        if not p["name"].startswith(PREFIX):
            continue
        for q in p["points"]:
            n += 1
            lv, gv = q["lvid"], q["gvid"]
            why = []
            if lv >= ai.count:
                why.append("level vertex %d >= %d nodes" % (lv, ai.count))
            else:
                if int(cross[lv]) != gv:
                    why.append("game vertex %d but the cross table says %d" % (gv, int(cross[lv])))
                d = ((ai.x[lv] - q["pos"][0]) ** 2 + (ai.z[lv] - q["pos"][2]) ** 2) ** 0.5
                walk = p["name"].endswith("_walk")
                if walk and p["name"][len(PREFIX) + 1:].split("_")[0] in ("1", "2", "3", "4", "5", "kuznetsov", "shtirts") and d > 1.5:
                    why.append("walk point %.1f m from its node" % d)
            if gv >= G.vc:
                why.append("game vertex %d >= %d" % (gv, G.vc))
            elif int(LEVEL_ID[gv]) != CORDON_ID:
                why.append("game vertex %d is on level id %d, not Cordon (%d)" % (gv, int(LEVEL_ID[gv]), CORDON_ID))
            if why:
                bad += 1
                print("  BAD  %-42s %-14s %s" % (p["name"], q["name"], "; ".join(why)))
    print("%s: %d bridge path points checked, %d problem(s)" % (label, n, bad))
    return bad


by = {p["name"]: p for p in P.paths}
next_cid = max(p["cid"] for p in P.paths) + 1
changed = 0
for name, pts in POSTS.items():
    new_pts = []
    for i, (pn, pos, flag) in enumerate(pts):
        lv, npos = node(pos)
        gv = int(cross[lv])
        # walk points sit on their AI node; look points keep the exact spot they look at (it can be off the mesh)
        ppos = list(struct.unpack("<3f", struct.pack("<3f", *(pos if name.endswith("_look") else npos))))
        new_pts.append(dict(idx=i, name=pn, pos=ppos, flags=flag, lvid=lv, gvid=gv, tail=b""))
        print("%-42s %-14s want (%.1f, %.1f, %.1f) node %d at (%.1f, %.1f, %.1f) gvid %d" % (name, pn, *pos, lv, *npos, gv))
    extra = {2: EDGES2} if len(pts) == 2 else {2: b""}
    if name in by:
        p = by[name]
        if p["points"] != new_pts or p["extra"] != extra:
            p["points"], p["extra"] = new_pts, extra
            changed += 1
    else:
        P.paths.append(dict(cid=next_cid, name=name, points=new_pts, extra=extra, other={}))
        next_cid += 1
        changed += 1
P.count = len(P.paths)
print("paths changed or added:", changed, " total paths", P.count)

if a.check or a.verify:
    bad = validate(P.paths, "plan applied to <in>")
    if a.check:
        print("<in> is %s" % ("already patched" if changed == 0 else "NOT patched yet (%d path(s) would change)" % changed))
        sys.exit(1 if bad else 0)
    # --verify: <in> is the patched file; changed must be 0 (the file already has the plan), then compare with the original
    problems = bad
    if changed:
        print("VERIFY FAIL: <in> does not contain the plan (%d path(s) differ)" % changed)
        problems += 1
    otop = X.chunks(open(a.verify, "rb").read())
    assert [c for c, _ in otop] == [0, 1, 2, 3, 4]
    for (cid, d), (_, od) in zip(top, otop):
        if cid != 3:
            same = d == od
            print("chunk %d: %s (%d bytes)" % (cid, "identical" if same else "DIFFERENT", len(d)))
            problems += 0 if same else 1
    OP = X.Patrols(dict(otop)[3])
    obyn = {p["name"]: p for p in OP.paths}
    nbyn = {p["name"]: p for p in X.Patrols(dict(top)[3]).paths}
    diff_posts, same_other, bad_other = 0, 0, 0
    for name, p in nbyn.items():
        if name in POSTS:
            diff_posts += 1
        elif name in obyn and obyn[name] == p:
            same_other += 1
        else:
            bad_other += 1
            print("  path %s differs from the original but is not in POSTS" % name)
    gone = [n for n in obyn if n not in nbyn]
    print("chunk 3: %d POSTS paths (changed or new), %d other paths identical, %d unexpected, %d missing; original %d paths, patched %d"
          % (diff_posts, same_other, bad_other, len(gone), len(obyn), len(nbyn)))
    problems += bad_other + len(gone)
    print("VERIFY", "FAIL" if problems else "PASS")
    sys.exit(1 if problems else 0)

out = b"".join(X.chunk(cid, P.pack() if cid == 3 else data) for cid, data in top)
open(a.dst, "wb").write(out)
validate(P.paths, "written file")
print("wrote", a.dst, len(out), "bytes (was %d)" % len(raw))
