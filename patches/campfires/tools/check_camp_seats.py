"""Offline check of every kamp (campfire sitting) job in the merged config tree against the level AI maps (no game, seconds).

  python check_camp_seats.py [--ai-root DIR] [--runs 400] [--fix]   (default ai-root: _ai next to this file, level.ai are extracted there)
  exit code 1 on any BAD line; --fix writes the `avoid = ...` line (stools and benches within reach of the ring) into every kamp section of the fire

For each fire (kamp centre) it prints: jobs (seats needed), AI node at the fire, the sectors of the ring that have no walkable node, how many
seats 1.1 m apart the ring can hold, furniture (smart_cover objects of the level) a seat could land on, and for the v1.4 seat rule
(random sector, exact node, falls back to the fire's own node) how often a run puts two stalkers on seats less than 1 m apart or on the fire node.
BAD: ring holds fewer separated seats than jobs, furniture within reach without an `avoid` entry in the kamp section, avoid entry without a cover.
"""
import collections
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camp_lib as C  # noqa: E402
import xrspawn as X  # noqa: E402

args = sys.argv[1:]
ai_root = os.path.join(C.HERE, "_ai")
runs = 400
if "--ai-root" in args:
    ai_root = args[args.index("--ai-root") + 1]
if "--runs" in args:
    runs = int(args[args.index("--runs") + 1])

# same numbers as scripts\xr_kamp.script
MIN_FIRE, MIN_GAP, SEAT_MAX_DY, FURN_R = 1.3, 1.1, 2.0, 1.0
SECT = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

# sit_normal / sit_high covers are a stool, chair or bench (a seat on it would be inside the furniture); stay_table / stay_wall are standing marks
covers = [(n, p) for n, p, kind in C.covers() if kind in ("animpoint_sit_normal", "animpoint_sit_high")]
bad = 0
ais = {}
fix = "--fix" in args


def fix_sections(camp, want):
    """put `avoid = <want>` into every kamp section at this fire (line right after `radius`), keeping the file's line endings."""
    for (path, sec) in camp["sections"]:
        raw = open(path, "rb").read()
        nl = "\r\n" if b"\r\n" in raw else "\n"
        lines = raw.decode("cp1251").split(nl)
        out, i, in_sec = [], 0, False
        while i < len(lines):
            ln = lines[i]
            if ln.strip().startswith("["):
                in_sec = ln.strip() == "[" + sec + "]"
            if in_sec and ln.split("=")[0].strip() == "avoid":
                i += 1
                continue
            out.append(ln)
            if in_sec and ln.split("=")[0].strip() == "radius" and want:
                pad = ln[:len(ln) - len(ln.lstrip())]
                out.append("avoid = " + want if not pad else pad + "avoid = " + want)
            i += 1
        new = nl.join(out).encode("cp1251")
        if new != raw:
            open(path, "wb").write(new)
            print("   fixed %s [%s]" % (os.path.relpath(path, C.REPO), sec))


def say(msg):
    print(msg)


def get_ai(level):
    if level not in ais:
        ais[level] = X.LevelAI(C.ensure_ai(level, ai_root))
    return ais[level]


for camp in C.camps():
    ai = get_ai(camp["level"])
    cx, cy, cz = camp["centre"]
    r0 = camp["radius"]
    prefix = C.LEVEL_PREFIX[camp["level"]] + "_"
    sel = np.where((np.abs(ai.x - cx) < 8) & (np.abs(ai.z - cz) < 8))[0]
    nodes = [(float(ai.x[n]), float(ai.y[n]), float(ai.z[n])) for n in sel]
    cells = collections.defaultdict(list)
    for n in sel:
        cells[(int(ai.xi[n]), int(ai.zi[n]))].append(float(ai.y[n]))

    def vertex(x, y, z):
        ix = int(round((x - ai.bb[0]) / ai.size))
        iz = int(round((z - ai.bb[2]) / ai.size))
        ys = cells.get((ix, iz))
        if not ys:
            return None
        yy = min(ys, key=lambda v: abs(v - y))
        return (ai.bb[0] + ix * ai.size, yy, ai.bb[2] + iz * ai.size)

    jobs = len(camp["jobs"])
    near = min(nodes, key=lambda p: math.dist(p, (cx, cy, cz))) if nodes else None
    fire_node = vertex(cx, cy, cz)
    say("%s fire %.1f %.1f %.1f radius %.1f, %d job(s) in %s" % (camp["level"], cx, cy, cz, r0, jobs, ", ".join(sorted(camp["files"]))))
    say("   AI node at the fire: %s" % ("none (hole in the map)" if fire_node is None else "y %.2f below..above %+.2f" % (fire_node[1], fire_node[1] - cy)))

    # furniture
    furn = [(n, p) for n, p in covers if n.startswith(prefix) and math.hypot(p[0] - cx, p[2] - cz) <= r0 + 0.4 + FURN_R and abs(p[1] - cy) < 2.5]
    if fix:
        fix_sections(camp, " | ".join("%.2f, %.2f, %.2f, %.1f" % (p[0], p[1], p[2], FURN_R) for n, p in furn))
        camp = [c for c in C.camps() if c["key"] == camp["key"]][0]
    for n, p in furn:
        for (path, sec), av in camp["sections"].items():
            ok = any(math.hypot(a[0] - p[0], a[2] - p[2]) < 0.6 and a[3] >= 0.9 for a in av)
            if not ok:
                say("   BAD furniture %s (%.2f m from the fire) is not in `avoid` of [%s] (%s)" % (n, math.hypot(p[0] - cx, p[2] - cz), sec, os.path.basename(path)))
                bad += 1
        say("   furniture %s at %.2f m from the fire" % (n, math.hypot(p[0] - cx, p[2] - cz)))
    for a in camp["avoid"]:
        if not any(math.hypot(p[0] - a[0], p[2] - a[2]) < 0.6 for _, p in covers):
            say("   BAD avoid entry %s matches no smart_cover of the level" % (a,))
            bad += 1

    # candidate nodes of the new seat rule
    def allowed(p):
        if abs(p[1] - cy) > SEAT_MAX_DY or math.hypot(p[0] - cx, p[2] - cz) < MIN_FIRE:
            return False
        return not any(math.hypot(p[0] - a[0], p[2] - a[2]) < a[3] for a in camp["avoid"])

    ring = [p for p in nodes if abs(math.hypot(p[0] - cx, p[2] - cz) - r0) <= 0.4 and allowed(p)]
    sectors_empty = []
    for i, (sx, sz) in enumerate(SECT):
        base = math.atan2(sz, sx)
        has = any(abs(((math.atan2(p[2] - cz, p[0] - cx) - base + math.pi) % (2 * math.pi)) - math.pi) <= 0.35 for p in ring)
        if not has:
            sectors_empty.append(i + 1)
    # greedy separated seats
    chosen = []
    for p in sorted(ring, key=lambda q: math.atan2(q[2] - cz, q[0] - cx)):
        if all(math.hypot(p[0] - q[0], p[2] - q[2]) >= MIN_GAP for q in chosen):
            chosen.append(p)
    say("   ring %.1f +- 0.4 m: %d usable nodes, room for %d seats %.1f m apart, sectors without a node: %s"
        % (r0, len(ring), len(chosen), MIN_GAP, sectors_empty or "none"))
    if len(chosen) < jobs:
        say("   BAD ring holds %d separated seats for %d jobs (stalkers would share seats)" % (len(chosen), jobs))
        bad += 1

    # v1.4 rule (random free sector, exact node, fire node as fallback): how often does it go wrong?
    rnd = random.Random(7)
    n_fire = n_close = 0
    for _ in range(runs):
        secs = rnd.sample(range(8), min(jobs, 8))
        seats = []
        for si in secs:
            sx, sz = SECT[si]
            m = math.hypot(sx, sz)
            dx, dz = sx / m + rnd.choice((-1, 0, 1)) / 6, sz / m + rnd.choice((-1, 0, 1)) / 6
            m = math.hypot(dx, dz)
            dx, dz = dx / m, dz / m
            r = r0 + (rnd.random() - 0.5) * 0.6
            v = None
            while v is None:
                v = vertex(cx + dx * r, cy, cz + dz * r)
                if v is None:
                    if r < 1:
                        v = vertex(cx, cy, cz)
                        break
                    r -= 0.5
            if v is not None:
                seats.append(v)
        if any(math.hypot(s[0] - cx, s[2] - cz) < MIN_FIRE for s in seats):
            n_fire += 1
        if any(math.hypot(a[0] - b[0], a[2] - b[2]) < 1.0 for i, a in enumerate(seats) for b in seats[i + 1:]):
            n_close += 1
    say("   v1.4 rule over %d runs: a seat on the fire node/barrel in %d%%, two seats under 1 m apart in %d%%" % (runs, 100 * n_fire // runs, 100 * n_close // runs))
    say("")

say("%d problem(s)" % bad)
sys.exit(1 if bad else 0)
