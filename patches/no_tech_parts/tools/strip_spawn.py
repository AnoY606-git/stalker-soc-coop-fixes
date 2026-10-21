"""Removes the technician parts (transistors, rosin, capacitors, copper wire, textolite) from an all.spawn.

  python strip_spawn.py <all.spawn> [<all.spawn> ...]          rewrite in place (atomic, refuses when the file changed meanwhile)
  python strip_spawn.py --check <all.spawn> [...]              only count, exit 1 when any part is still in the file

The mod's Cordon, Garbage and Agroprom carry 63 of these items (the CoP quest items `jup_b200_tech_materials_*`, they are not in the
original SoC). Entities of those sections are dropped and the remaining ones get contiguous ids again: the chunk id and the `spawn_id`
field inside every packet (they are equal in this file); the file has no parent ids and an empty spawn graph, so nothing else refers to
the ids; the header count is rewritten by the writer. Order of the other entities is kept.
Needs patches/soc_levels/tools/xrspawn.py (round trip of an untouched file is byte identical).
Run it LAST on a regenerated all.spawn (darkvalley_restore/tools/make_all_spawn.py, cordon_bridge/tools/make_paths.py).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "soc_levels", "tools")))
import xrspawn as X  # noqa: E402

FAMILY = (
    "jup_b200_tech_materials_wire",        # Coil of copper wire
    "jup_b200_tech_materials_acetone",     # Can of rosin (the section name says acetone)
    "jup_b200_tech_materials_textolite",   # Textolite base
    "jup_b200_tech_materials_transistor",  # Box of transistors
    "jup_b200_tech_materials_capacitor",   # Pack of capacitors
)


SPAWN_ID_OFF = 18  # u16 after respawn, id, parent, phantom, flags, version, 3 x u16 (see darkvalley_restore/tools/make_all_spawn.py)


def spawn_id(e):
    return struct.unpack_from("<H", e.pk, e.p_f + SPAWN_ID_OFF)[0]


def is_part(e):
    return e.section in FAMILY or "tech_materials" in e.name


def process(path, check):
    st = os.stat(path)
    raw = open(path, "rb").read()
    S = X.AllSpawn(raw)
    parts = [e for e in S.ents if is_part(e)]
    print("%s: %d entities, %d technician parts" % (path, len(S.ents), len(parts)))
    if check:
        for e in parts:
            print("  still there: %s %s" % (e.section, e.name))
        return len(parts)
    if not parts:
        return 0
    for e in S.ents:
        assert spawn_id(e) == e.eid, "packet spawn id differs from the chunk id: %s %s" % (e.section, e.name)
    S.ents = [e for e in S.ents if not is_part(e)]
    for i, e in enumerate(S.ents):
        e.eid = i
        struct.pack_into("<H", e.pk, e.p_f + SPAWN_ID_OFF, i)
    out = S.pack()
    chk = X.AllSpawn(out)
    assert len(chk.ents) == len(S.ents) and not any(is_part(e) for e in chk.ents)
    assert all(e.eid == i and spawn_id(e) == i for i, e in enumerate(chk.ents))
    assert [e.name for e in chk.ents] == [e.name for e in S.ents]
    st2 = os.stat(path)
    if (st2.st_mtime_ns, st2.st_size) != (st.st_mtime_ns, st.st_size):
        sys.exit("%s changed while it was processed, nothing written" % path)
    tmp = path + ".tmp_strip"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)
    print("  removed %d, now %d entities, %d bytes" % (len(parts), len(S.ents), len(out)))
    return 0


def main():
    args = sys.argv[1:]
    check = "--check" in args
    files = [a for a in args if a != "--check"]
    if not files:
        sys.exit(__doc__)
    left = sum(process(p, check) for p in files)
    sys.exit(1 if (check and left) else 0)


if __name__ == "__main__":
    main()
