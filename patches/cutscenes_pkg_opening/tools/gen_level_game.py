"""Move the four Cordon co-op spawn points (team 4, game type 128) into Sidorovich's bunker, in the room in front of his counter
(original SoC start). The counter room is x -248.2 to -241, z -135.9 to -132.7; the counter (desk) stands at x -246.0 to -245.7 and
blocks the room from wall to wall, Sidorovich sits behind it at (-244.69, -24.96, -133.96). The space in front of the counter
(between the door wall and the counter) is about 2.2 x 2.6 m. The first room west of the door (x -250.6 to -249.2) is OUTSIDE:
no point there any more (players spawned behind the door).
usage: gen_level_game.py <in level.game> <out level.game> [level.ai for node check]"""
import os, sys
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\documents\workspace\games\clear-sky-coop\tools\levels"))
import add_rpoints as A

src, dst = sys.argv[1], sys.argv[2]
d = open(src, "rb").read()
cur = A.parse_rpoints(d)
# AI nodes of the room in front of the counter (verified against level.ai): x -247.8 (doorway cell), -247.1, -246.4; z -133.7, -134.4, -135.1.
# Only three points fit with the 1.4 m spacing of the stock Cordon points; the fourth is the best that is left (0.7 to 1.0 m).
Y = -24.8
TRADER = (-244.69, -133.96)
pts = [(-246.4, Y, -133.7), (-246.4, Y, -135.1), (-247.8, Y, -134.4), (-247.1, Y, -134.4)]
# the engine hands out a spawn point only when no player stands near it: 0.7 m spacing (first try) let only one of two clients spawn.
import math
def yaw_to(p):
    # same convention as set_actor_direction: -atan2(dx, dz), facing Sidorovich
    return -math.atan2(TRADER[0] - p[0], TRADER[1] - p[2])
keep = [p for p in cur if not (p["team"] == A.COOP_TEAM and p["gt"] == A.COOP_GT)]
new = [dict(team=A.COOP_TEAM, pos=p, yaw=yaw_to(p), gt=A.COOP_GT) for p in pts]
if len(sys.argv) > 3:
    ai = A.LevelAI(sys.argv[3])
    for p in new:
        r = ai.nearest(*p["pos"])
        print("node distance %.2f for %s" % (r[0], p["pos"]))
        assert r[0] < 0.6, "not on an AI node"
for i in range(len(pts)):
    for j in range(i + 1, len(pts)):
        print("spacing %s - %s: %.2f m" % (pts[i][::2], pts[j][::2], math.hypot(pts[i][0] - pts[j][0], pts[i][2] - pts[j][2])))
out = A.rewrite(d, keep + new)
open(dst, "wb").write(out)
chk = A.parse_rpoints(out)
print("wrote", dst, len(chk), "rpoints,", sum(1 for p in chk if p["team"] == 4), "team 4")
