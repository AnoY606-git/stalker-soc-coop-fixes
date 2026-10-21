"""Check (and list candidates for) the campfire spots where non-story players start (coop_soc_opening.script, CAMP_SPOTS).
  python gen_camp_spots.py <Cordon level.ai>            checks the spots written in the script
  python gen_camp_spots.py <Cordon level.ai> --list     prints ring candidates (radius 4.2 m around the fire, every 15 degrees)
Rules: the spot is an AI node (within 0.1 m), all eight neighbour nodes exist, y within 0.8 m of the fire floor, 3.5 to 5 m from the fire
(the sitting seats of the village stalkers are at 2.3 to 2.8 m), spots at least 4 m apart (the engine hands a point out only while nobody stands near it).
level.ai: extract coop_l01_escape\\level.ai from the mod (tools\\xdb.py extract)."""
import math
import os
import re
import sys

sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\documents\workspace\games\clear-sky-coop\tools\levels"))
import add_rpoints as A

ai = A.LevelAI(sys.argv[1])
FX, FY, FZ = -206.9, -19.6, -140.1


def neighbours_ok(x, y, z):
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            r = ai.nearest(x + i * ai.cell, y, z + j * ai.cell, rad=2)
            if r is None or abs(r[1][0] - (x + i * ai.cell)) > 0.36 or abs(r[1][2] - (z + j * ai.cell)) > 0.36 or abs(r[1][1] - y) > 0.8:
                return False
    return True


if '--list' in sys.argv:
    for ang in range(0, 360, 15):
        a = math.radians(ang)
        r = ai.nearest(FX + 4.2 * math.cos(a), FY, FZ + 4.2 * math.sin(a), rad=3)
        if r:
            nx, ny, nz = r[1]
            print('%3d  { x = %.2f, y = %.2f, z = %.2f },  fire %.2f m  neighbours %s' % (ang, nx, ny, nz, math.hypot(nx - FX, nz - FZ), neighbours_ok(nx, ny, nz)))
    sys.exit(0)

here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(os.path.dirname(here), 'gamedata', 'scripts', 'coop_soc_opening.script'), encoding='utf8').read()
block = src[src.index('CAMP_SPOTS = {'):]
block = block[:block.index('}\n')]
spots = [tuple(float(v) for v in m) for m in re.findall(r'x = (-?[\d.]+), y = (-?[\d.]+), z = (-?[\d.]+)', block)]
bad = 0
for s in spots:
    r = ai.nearest(*s, rad=3)
    nd = math.sqrt((r[1][0] - s[0]) ** 2 + (r[1][1] - s[1]) ** 2 + (r[1][2] - s[2]) ** 2)
    fd = math.hypot(s[0] - FX, s[2] - FZ)
    ok = nd < 0.1 and neighbours_ok(*s) and abs(s[1] - FY) < 0.8 and 3.5 <= fd <= 5.0
    bad += 0 if ok else 1
    print('spot %s: node distance %.2f, neighbours %s, fire distance %.2f -> %s' % (s, nd, neighbours_ok(*s), fd, 'ok' if ok else 'BAD'))
for i in range(len(spots)):
    for j in range(i + 1, len(spots)):
        d = math.hypot(spots[i][0] - spots[j][0], spots[i][2] - spots[j][2])
        if d < 4.0:
            bad += 1
        print('spacing %d-%d: %.2f m%s' % (i + 1, j + 1, d, '' if d >= 4.0 else '  TOO CLOSE'))
print('%d spots, %d problem(s)' % (len(spots), bad))
sys.exit(1 if bad else 0)
