"""Removes ONE anomaly zone on the Bar (coop_l05_bar): the gravitational mine in front of the Garbage -> Bar arrival (FOSTER's request).
Every other Bar anomaly stays or is put back.

  python strip_bar_anomalies.py <all.spawn> [...]                      rewrite in place (atomic, refuses when the file changed meanwhile)
  python strip_bar_anomalies.py --ref <original all.spawn> <all.spawn> [...]
                                                                       the same, and re-adds every Bar anomaly zone of the original that is
                                                                       missing (restores what an earlier version of this tool removed)
  python strip_bar_anomalies.py --check [--ref <orig>] <all.spawn> [...]   only list, exit 1 when FOSTER's zone is still in (or, with --ref, a
                                                                       zone is missing)
  python strip_bar_anomalies.py --level-spawn <in level.spawn> <out level.spawn>    same for the Bar's level.spawn (new file, input untouched)
  python strip_bar_anomalies.py --report <all.spawn>                   print every Bar anomaly zone with its distance to the nearest arrival

History: FOSTER, "in the Bar, right in front of the level transition, remove the anomaly, it stands too close to the spawn". The anomaly in
his screenshot is the Garbage -> Bar arrival one (level_prefix_zone_mine_gravitational_strong, 12.1 m from the arrival point, bearing 323
degrees). The first version removed every zone within 30 m of an arrival point (10 zones); FOSTER then answered "return all but one", so the
rule is now: exactly this one zone (section zone_mine_gravitational_strong, name level_prefix_zone_mine_gravitational_strong, at
354.7, 9.3, -178.0) is dropped, every other Bar zone is the original SoC one. The original SoC all.spawn of the mod lives in
`Shadow of COOP 8.0/addon_unpacked` (extract `spawns/all.spawn` with tools/xdb.py, pass it as --ref).

Arrival points (all Bar coordinates, read from the dest_position of the level changers in the mod's all.spawn, and from the Bar's level.game);
used by --report only:
  Garbage -> Bar        gar_bar_level_changer   (361.9, 11.0, -187.6)
  Rostok -> Bar         ros_bar_level_changer   ( 55.3,  0.0,  140.0)
  Wild Territory -> Bar mil_bar_level_changer   ( 57.1,  0.0,  169.4)
  Cordon guide -> Bar   6_esc_bar_guide_level_changer (169.4, 0.0, 65.8)  (the party vote route of the test harness)
  co-op spawn points (team 4, level.game)   (105.0, -15.8, -10.5 ) and the neutral ones at x 108.5 (no anomaly near them)

Composable with no_tech_parts/tools/strip_spawn.py and any other in-place all.spawn step: this tool selects by section, name and position
(never by id), renumbers the spawn ids contiguously exactly like strip_spawn.py does (id in the chunk == spawn id in the packet), and can be run
in any order and any number of times (a second run finds nothing to do). A restored zone is inserted right after the entity that preceded it
in the original (the nearest preceding one that the target still has), so the order of the original is kept.
Needs patches/soc_levels/tools/xrspawn.py.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "soc_levels", "tools")))
import xrspawn as X  # noqa: E402

BAR = "coop_l05_bar"
# The one zone that stays removed: FOSTER's (12.1 m in front of the Garbage -> Bar arrival point).
FOSTER_SECTION = "zone_mine_gravitational_strong"
FOSTER_NAME = "level_prefix_zone_mine_gravitational_strong"
FOSTER_POS = (354.7, 9.3, -178.0)
FOSTER_TOL = 1.0  # m
ARRIVALS = {
    "gar_bar_level_changer": (361.9, 11.0, -187.6),
    "ros_bar_level_changer": (55.3, 0.0, 140.0),
    "mil_bar_level_changer": (57.1, 0.0, 169.4),
    "6_esc_bar_guide_level_changer": (169.4, 0.0, 65.8),
    "coop_spawn_points": (105.0, -15.8, -10.5),
    "neutral_spawn_points": (108.5, -15.8, -10.5),
}
SPAWN_ID_OFF = 18  # same field as strip_spawn.py


def is_zone(section):
    return section.startswith("zone_")


def nearest(pos):
    best = None
    for k, v in ARRIVALS.items():
        d = math.dist(v, pos)
        if best is None or d < best[0]:
            best = (d, k)
    return best


def doomed(section, name, pos):
    """True for FOSTER's zone only (selected by section, name and position, never by id)."""
    return section == FOSTER_SECTION and name == FOSTER_NAME and math.dist(pos, FOSTER_POS) < FOSTER_TOL


def spawn_id(e):
    return struct.unpack_from("<H", e.pk, e.p_f + SPAWN_ID_OFF)[0]


def bar_level_ids(S):
    return {l["id"] for l in S.graph.levels if l["name"] == BAR}


def bar_zones(S):
    ids = bar_level_ids(S)
    lvl = S.graph.level_id
    out = []
    for e in S.ents:
        if is_zone(e.section) and int(lvl[e.gvid]) in ids:
            out.append(e)
    return out


def doomed_entities(S):
    return [e for e in bar_zones(S) if doomed(e.section, e.name, e.pos)]


def key(e):
    return (e.section, e.name)


def line(e):
    d, k = nearest(e.pos)
    return "%s %s (%.1f, %.1f, %.1f) %.1f m from %s" % (e.section, e.name, e.pos[0], e.pos[1], e.pos[2], d, k)


def missing_from(S, R):
    """Bar zones of the original R that S lacks (FOSTER's excluded), as (index in R.ents, entity)."""
    have = {key(e) for e in S.ents}
    bz = {id(e) for e in bar_zones(R)}
    return [(i, e) for i, e in enumerate(R.ents)
            if id(e) in bz and key(e) not in have and not doomed(e.section, e.name, e.pos)]


def restore(S, R, miss):
    """Insert every (index, zone) of miss into S.ents right after the nearest preceding original entity that S has."""
    for i, e in miss:
        pos = {key(x): n for n, x in enumerate(S.ents)}
        at = 0
        for j in range(i - 1, -1, -1):
            n = pos.get(key(R.ents[j]))
            if n is not None:
                at = n + 1
                break
        c = X.Entity(e.eid, e.payload())  # private copy of the original entity
        S.ents.insert(at, c)


def process(path, check, ref):
    st = os.stat(path)
    raw = open(path, "rb").read()
    S = X.AllSpawn(raw)
    gone = doomed_entities(S)
    miss = missing_from(S, ref) if ref is not None else []
    print("%s: %d entities, FOSTER's zone present: %d%s" % (
        path, len(S.ents), len(gone), "" if ref is None else ", original Bar zones missing: %d" % len(miss)))
    for e in gone:
        print("  %s %s" % ("still there:" if check else "remove:", line(e)))
    for i, e in miss:
        print("  %s %s" % ("missing:" if check else "restore:", line(e)))
    if check:
        return len(gone) + len(miss)
    if not gone and not miss:
        return 0
    for e in S.ents:
        assert spawn_id(e) == e.eid, "packet spawn id differs from the chunk id: %s %s" % (e.section, e.name)
    drop = {id(e) for e in gone}
    S.ents = [e for e in S.ents if id(e) not in drop]
    if miss:
        restore(S, ref, miss)
    for i, e in enumerate(S.ents):
        e.eid = i
        struct.pack_into("<H", e.pk, e.p_f + SPAWN_ID_OFF, i)
    out = S.pack()
    chk = X.AllSpawn(out)
    assert len(chk.ents) == len(S.ents) and not doomed_entities(chk)
    assert all(e.eid == i and spawn_id(e) == i for i, e in enumerate(chk.ents))
    assert [e.name for e in chk.ents] == [e.name for e in S.ents]
    if ref is not None:
        assert not missing_from(chk, ref)
    st2 = os.stat(path)
    if (st2.st_mtime_ns, st2.st_size) != (st.st_mtime_ns, st.st_size):
        sys.exit("%s changed while it was processed, nothing written" % path)
    tmp = path + ".tmp_strip_bar"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)
    print("  removed %d, restored %d, now %d entities, %d bytes" % (len(gone), len(miss), len(S.ents), len(out)))
    return 0


def level_spawn(src, dst):
    """level.spawn = flat chunks, chunk id = index, payload = u16 + section\0 name\0 + packet. Only FOSTER's chunk is dropped and the ids
    renumbered; the spawn ids inside the packets are the compiler's level-local numbers and are left alone (nothing reads them there)."""
    raw = open(src, "rb").read()
    ch = X.chunks(raw)
    keep, gone = [], []
    for cid, p in ch:
        z = p.index(b"\0", 2)
        z2 = p.index(b"\0", z + 1)
        sec = p[2:z].decode("latin1")
        name = p[z + 1:z2].decode("latin1")
        pos = struct.unpack_from("<3f", p, z2 + 1 + 2)
        if doomed(sec, name, pos):
            gone.append((sec, name, pos))
        else:
            keep.append(p)
    out = b"".join(X.chunk(i, p) for i, p in enumerate(keep))
    for sec, name, pos in gone:
        d, k = nearest(pos)
        print("  remove: %s %s (%.1f, %.1f, %.1f) %.1f m from %s" % (sec, name, pos[0], pos[1], pos[2], d, k))
    with open(dst, "wb") as f:
        f.write(out)
    print("level.spawn: %d -> %d chunks, wrote %s (%d bytes)" % (len(ch), len(keep), dst, len(out)))


def report(path):
    S = X.AllSpawn(open(path, "rb").read())
    rows = sorted(((nearest(e.pos)[0], e) for e in bar_zones(S)), key=lambda r: r[0])
    print("%d Bar anomaly zones" % len(rows))
    for d, e in rows:
        print("%s%s" % ("REMOVE  " if doomed(e.section, e.name, e.pos) else "keep    ", line(e)))


def main():
    args = sys.argv[1:]
    if args and args[0] == "--level-spawn":
        if len(args) != 3:
            sys.exit(__doc__)
        level_spawn(args[1], args[2])
        return
    if args and args[0] == "--report":
        report(args[1])
        return
    ref = None
    if "--ref" in args:
        i = args.index("--ref")
        ref = X.AllSpawn(open(args[i + 1], "rb").read())
        del args[i:i + 2]
    check = "--check" in args
    files = [a for a in args if a != "--check"]
    if not files:
        sys.exit(__doc__)
    left = sum(process(p, check, ref) for p in files)
    sys.exit(1 if (check and left) else 0)


if __name__ == "__main__":
    main()
