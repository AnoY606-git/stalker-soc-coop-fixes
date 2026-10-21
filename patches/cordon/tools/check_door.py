"""Offline check of Sidorovich's bunker door logic (esc_trader_door.ltx), no game needed.

  python check_door.py [--spawn <all.spawn>]     default: patches\\darkvalley_restore\\gamedata\\spawns\\all.spawn

What it does
  1. reads the shipped esc_trader_door.ltx and the zones from all.spawn (box of every space_restrictor the door uses, exact rotation),
  2. checks the file: every switch target exists, the start section is `close`, `close` can be opened by use, `open` has no `on_use`
     (it must never be closed in somebody's face), every zone the door names exists on Cordon,
  3. runs the xr_logic switch rules (any player in zone / no player in zone, use) over walks of 1 to 2 players:
        entrance stairs -> corridor -> door -> Sidorovich's room (and back), a player spawned in front of the counter, a camp player
     and asserts: the door is open whenever a player is inside the bunker (also on the stairs down), closed only when nobody is,
     and never closes while a player stands at the door,
  4. does the same with the v1.4 file (git show HEAD:...) to show the old behaviour (a player at the door cannot keep it open).
Exit code 1 on any failed assert."""
import math
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(PATCH, "..", ".."))
LTX = os.path.join(PATCH, "gamedata", "configs", "scripts", "coop_l01_escape", "esc_trader_door.ltx")
SPAWN = os.path.join(REPO, "patches", "darkvalley_restore", "gamedata", "spawns", "all.spawn")
if "--spawn" in sys.argv:
    SPAWN = sys.argv[sys.argv.index("--spawn") + 1]
sys.path.insert(0, os.path.join(REPO, "patches", "level_back", "tools"))
import lc_lib as C  # noqa: E402

X = C.X
fails = []


def check(cond, msg):
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def ini_text(txt):
    secs, cur = {}, None
    for raw in txt.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            cur = m.group(1).strip()
            secs[cur] = {}
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            secs[cur][k.strip()] = v.strip()
    return secs


# ------------------------------------------------------------------ zones from all.spawn
print("reading %s" % SPAWN)
S = X.AllSpawn(open(SPAWN, "rb").read())
names = C.level_names(S)
ZONES = {}
DOOR = None
for e in S.ents:
    if e.section == "space_restrictor" or e.name == "esc_trader_door":
        try:
            if names[int(S.graph.level_id[e.gvid])] != "coop_l01_escape":
                continue
        except Exception:
            continue
    if e.name == "esc_trader_door":
        DOOR = e.pos
    if e.section == "space_restrictor" and e.name in ("esc_trader_door_space_restrictor", "esc_sr_no_weapon_space_restrictor"):
        pk = bytes(e.pk)
        ms = C.SHAPE_RE.search(pk, e.p_lv)
        f = struct.unpack_from("<12f", pk, ms.end())
        ZONES[e.name] = (e, dict(size=(f[0], f[4], f[8]), offset=tuple(f[9:12])))
check(DOOR is not None, "door object esc_trader_door found on Cordon at (%.2f, %.2f, %.2f)" % (DOOR or (0, 0, 0)))
for n in ("esc_trader_door_space_restrictor", "esc_sr_no_weapon_space_restrictor"):
    check(n in ZONES, "zone %s exists on Cordon" % n)


def inside(zone, pt):
    e, info = ZONES[zone]
    return C.box_distance(e, info, pt) == 0.0


# ------------------------------------------------------------------ the xr_logic model of ph_door
class Door:
    def __init__(self, secs):
        self.secs = secs
        self.sec = secs["logic"]["active"]

    def settle(self, players):
        """evaluate the switch conditions (zone checks) until nothing switches; returns the sequence of sections."""
        seq = [self.sec]
        for _ in range(6):
            s = self.secs[self.sec]
            target = None
            for key, val in s.items():
                if key.startswith("on_actor_in_zone") or key.startswith("on_actor_not_in_zone"):
                    zone, _, tgt = [v.strip() for v in val.partition("|")]
                    any_in = any(inside(zone, p) for p in players)
                    if (key.startswith("on_actor_in_zone") and any_in) or (key.startswith("on_actor_not_in_zone") and not any_in):
                        target = tgt
                        break
                elif key == "on_info" and "{" not in val:
                    target = val.split()[0]
                    break
            if target is None:
                break
            self.sec = target
            seq.append(target)
        return seq

    def use(self, players):
        s = self.secs[self.sec]
        if "on_use" in s:
            self.sec = s["on_use"].split()[0]
        return self.settle(players)

    @property
    def is_open(self):
        return self.secs[self.sec].get("closed", "true") == "false"


def validate(secs, label, new):
    print("== %s" % label)
    check(secs["logic"]["active"] in secs, "start section %s exists" % secs["logic"]["active"])
    for name, s in secs.items():
        for key, val in s.items():
            if key.startswith("on_use") or key.startswith("on_info") or "zone" in key:
                tgt = val.split("|")[-1].strip().split()
                tgt = [t for t in tgt if t.startswith("ph_door@")]
                for t in tgt:
                    check(t in secs, "[%s] %s -> %s exists" % (name, key, t))
            if "zone" in key:
                z = val.partition("|")[0].strip()
                check(z in ZONES, "[%s] %s names zone %s which exists" % (name, key, z))
    if new:
        check(secs["logic"]["active"] == "ph_door@close", "the door starts closed (stock)")
        check("on_use" in secs["ph_door@close"] and secs["ph_door@close"]["on_use"].startswith("ph_door@open"), "closed door opens on use")
        check("on_use" not in secs["ph_door@open"], "open door has no on_use (never closed in somebody's face)")
        check(secs["ph_door@open"].get("locked") == "false" and secs["ph_door@close"].get("locked") == "false", "never locked")
        check("dev_flash" not in open(LTX).read(), "no dependency on the flash drive item")


# ------------------------------------------------------------------ walks
P = lambda x, y, z: (x, y, z)
STAIRS_TOP = P(-253.4, -20.3, -126.7)
RAMP = P(-254.1, -22.5, -131.0)
STAIRS_BOTTOM = P(-254.1, -23.4, -134.4)
CORRIDOR = P(-252.0, -24.4, -134.4)
FIRST_ROOM = P(-249.9, -24.8, -134.4)
AT_DOOR = P(-248.25, -24.8, -134.3)
FRONT_ROOM = P(-247.1, -24.8, -134.4)
SIDOR = P(-244.9, -24.8, -134.4)
VILLAGE = P(-243.0, -19.4, -123.9)
CAMPFIRE = P(-206.9, -19.6, -140.1)
SPAWNS = [P(-246.4, -24.8, -133.7), P(-246.4, -24.8, -135.1), P(-247.8, -24.8, -134.4), P(-247.1, -24.8, -134.4)]


def walk(secs, label, steps, expect_new):
    """steps: list of (description, [player positions], use_pressed, expected door state or None)"""
    print("== %s" % label)
    d = Door(secs)
    ok = True
    for desc, players, use, want in steps:
        seq = d.use(players) if use else d.settle(players)
        state = "open" if d.is_open else "closed"
        line = "%-46s sections %-40s -> %s" % (desc, " > ".join(s.replace("ph_door@", "") for s in seq), state)
        if want is None:
            print("        " + line)
            continue
        good = (state == want)
        if expect_new:
            check(good, line + "   (want %s)" % want)
        else:
            print(("  ok    " if good else "  OLD   ") + line + "   (want %s)" % want)
        ok = ok and good
    return ok


def scenarios(secs, expect_new):
    walk(secs, "one player enters from the village and goes to Sidorovich, then leaves", [
        ("in the village", [VILLAGE], False, "closed"),
        ("top of the entrance stairs", [STAIRS_TOP], False, None),
        ("on the ramp (inside the bunker box)", [RAMP], False, "open"),
        ("stairs bottom", [STAIRS_BOTTOM], False, "open"),
        ("corridor", [CORRIDOR], False, "open"),
        ("first room, presses use at the door", [FIRST_ROOM], True, "open"),
        ("standing at the door", [AT_DOOR], False, "open"),
        ("press use at the door again", [AT_DOOR], True, "open"),
        ("in front of Sidorovich's counter", [FRONT_ROOM], False, "open"),
        ("at Sidorovich (hand-in of the flash drive)", [SIDOR], False, "open"),
        ("back at the door, use", [AT_DOOR], True, "open"),
        ("out in the village again", [VILLAGE], False, "closed"),
        ("comes back: ramp", [RAMP], False, "open"),
    ], expect_new)
    walk(secs, "story player spawned in front of the counter, then walks out", [
        ("spawn point 1 (bunker)", [SPAWNS[0]], False, "open"),
        ("press use at the door", [AT_DOOR], True, "open"),
        ("at the door with nobody else", [AT_DOOR], False, "open"),
        ("stairs bottom", [STAIRS_BOTTOM], False, "open"),
        ("village", [VILLAGE], False, "closed"),
    ], expect_new)
    walk(secs, "four players in the bunker, one walks to the village", [
        ("all four at the spawn points", SPAWNS, False, "open"),
        ("three in the bunker, one in the village", SPAWNS[:3] + [VILLAGE], False, "open"),
        ("last one leaves", [VILLAGE, CAMPFIRE], False, "closed"),
    ], expect_new)
    walk(secs, "non-story player: campfire, then walks to the bunker with the flash drive", [
        ("at the campfire", [CAMPFIRE], False, "closed"),
        ("in the village near the bunker", [VILLAGE], False, "closed"),
        ("down the ramp", [RAMP], False, "open"),
        ("at the door (use)", [AT_DOOR], True, "open"),
        ("in front of the counter", [FRONT_ROOM], False, "open"),
    ], expect_new)


new = ini_text(open(LTX, encoding="ascii").read())
validate(new, "shipped esc_trader_door.ltx", True)
scenarios(new, True)

try:
    old_txt = subprocess.check_output(["git", "-C", REPO, "show", "HEAD:patches/cordon/gamedata/configs/scripts/coop_l01_escape/esc_trader_door.ltx"]).decode("ascii")
    if "esc_sr_no_weapon_space_restrictor" in old_txt:
        print("HEAD already has the new file, old-behaviour comparison skipped")
    else:
        print("\n---- the v1.4 file (git HEAD), for comparison only: 'OLD' lines are the failures players saw ----")
        scenarios(ini_text(old_txt), False)
        old = ini_text(old_txt)
        # the cause in one number: where is the old zone relative to the door
        z = "esc_trader_door_space_restrictor"
        e, info = ZONES[z]
        print("old zone %s: centre (%.1f, %.1f, %.1f), size %.2f x %.2f x %.2f; door at (%.2f, %.2f, %.2f): %.1f m away" % (
            z, e.pos[0], e.pos[1], e.pos[2], info["size"][0], info["size"][1], info["size"][2], DOOR[0], DOOR[1], DOOR[2],
            math.sqrt(sum((e.pos[i] - DOOR[i]) ** 2 for i in range(3)))))
        check(not inside(z, AT_DOOR) and not inside(z, FRONT_ROOM) and not inside(z, SIDOR), "old zone does NOT contain the door, the counter room or Sidorovich (cause)")
except Exception as ex:  # git missing or the file is new: not fatal
    print("old file comparison skipped: %s" % ex)

print("\n%d failed assert(s)" % len(fails))
sys.exit(1 if fails else 0)
