"""Move the four Cordon co-op spawn points (team 4, game type 128) into Sidorovich's bunker (original SoC start).
usage: gen_level_game.py <in level.game> <out level.game> [level.ai for node check]"""
import os, sys
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\documents\workspace\games\clear-sky-coop\tools\levels"))
import add_rpoints as A

src, dst = sys.argv[1], sys.argv[2]
d = open(src, "rb").read()
cur = A.parse_rpoints(d)
# bunker AI nodes (verified against level.ai): the Marked One stands in front of the desk facing Sidorovich (-244.69, -24.96, -133.96)
Y = -24.96
YAW = -1.735   # direction (dx 2.4, dz -0.4) -> -atan2(dx, dz)
# the engine hands out a spawn point only when no player stands near it: keep at least 1.4 m between points (stock Cordon: 1.4 and 2.8 m).
# 0.7 m spacing (first try) let only one of two clients spawn on a dedicated server.
pts = [(-247.1, Y, -135.1), (-247.1, Y, -133.7), (-248.5, Y, -134.4), (-249.9, Y, -134.4)]
keep = [p for p in cur if not (p["team"] == A.COOP_TEAM and p["gt"] == A.COOP_GT)]
new = [dict(team=A.COOP_TEAM, pos=p, yaw=YAW, gt=A.COOP_GT) for p in pts]
if len(sys.argv) > 3:
    ai = A.LevelAI(sys.argv[3])
    for p in new:
        r = ai.nearest(*p["pos"])
        print("node distance %.2f for %s" % (r[0], p["pos"]))
        assert r[0] < 0.6, "not on an AI node"
out = A.rewrite(d, keep + new)
open(dst, "wb").write(out)
chk = A.parse_rpoints(out)
print("wrote", dst, len(chk), "rpoints,", sum(1 for p in chk if p["team"] == 4), "team 4")
