"""Shared helpers of the campfire checkers (check_camp_seats.py, check_camp_jobs.py): merged config lookup, ltx parser, level.ai access.

The "merged tree" is what build.py ships: every patches/<fix>/gamedata in sorted order (the last copy of a file wins), with the files of the
unfinished patches left out (SKIP, the same list as in stalker.md section 3), on top of the original mod configs (BASE, db0 of Shadow of COOP 8.0).
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(PATCH, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "patches", "soc_levels", "tools"))
sys.path.insert(0, os.path.join(REPO, "tools"))

SKIP = {"soc_levels", "weapon_upgrades", "npc_attachments", "arrival_facing", "inventory_carry"}
BASE = os.path.expandvars(r"%USERPROFILE%\Downloads\Shadow of COOP 8.0\source\gamedata.db0")
ADDON_UNPACKED = os.path.expandvars(r"%USERPROFILE%\Downloads\Shadow of COOP 8.0\addon_unpacked")
SPAWN_REL = os.path.join("spawns", "all.spawn")

LEVEL_PREFIX = {"coop_l01_escape": "esc", "coop_l02_garbage": "gar", "coop_l05_bar": "bar", "coop_l07_military": "mil"}


def merged(rel, skip=SKIP):
    """absolute path of the file `rel` (relative to gamedata) as the release db would carry it, or the base mod file, or None."""
    found = None
    pdir = os.path.join(REPO, "patches")
    for fix in sorted(os.listdir(pdir)):
        if fix in skip:
            continue
        p = os.path.join(pdir, fix, "gamedata", rel)
        if os.path.isfile(p):
            found = p
    if found:
        return found
    p = os.path.join(BASE, rel)
    return p if os.path.isfile(p) else None


def merged_list(rel_dir, skip=SKIP):
    """relative paths of every file below gamedata\\<rel_dir> in the merged tree (patches and base)."""
    out = set()
    pdir = os.path.join(REPO, "patches")
    roots = [os.path.join(BASE, rel_dir)]
    for fix in sorted(os.listdir(pdir)):
        if fix not in skip:
            roots.append(os.path.join(pdir, fix, "gamedata", rel_dir))
    for r in roots:
        for d, _, fs in os.walk(r):
            for f in fs:
                out.add(os.path.relpath(os.path.join(d, f), r).replace("\\", "/"))
    return sorted(out)


def ini(path):
    """{section: {key: value}} plus the section order; comments (;) stripped; `a:b` inheritance after the name is ignored."""
    secs, order, cur = {}, [], None
    for raw in open(path, "rb").read().decode("cp1251", "replace").splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            cur = m.group(1).strip()
            secs.setdefault(cur, {})
            order.append(cur)
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            secs[cur][k.strip()] = v.strip()
        elif cur is not None:
            secs[cur][line] = ""
    return secs, order


def nums(text):
    return [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", text)]


def _reach(secs, start):
    """sections reachable from `start` through on_info / on_timer-style transitions (names of the form scheme@name found in values)."""
    seen, todo = set(), [start]
    while todo:
        cur = todo.pop()
        if cur in seen or cur not in secs:
            continue
        seen.add(cur)
        for k, v in secs[cur].items():
            if k == "active" or k.startswith("on_") or k in ("on_info", "on_timer", "on_signal", "on_actor_dist_le", "on_actor_dist_ge"):
                for tok in re.findall(r"[a-z_0-9]+@[A-Za-z_0-9]+", v):
                    todo.append(tok)
    return seen


def camps():
    """Every fire that a [kamp@...] section sits at, in the merged configs (a job counts for a fire when its section chain reaches a kamp section there).
    -> list of dict(level, key, centre, radius, avoid [(x, y, z, r)], jobs [(file, logic section)], files, sections {(path, kamp section): avoid list})"""
    out = {}
    for rel in merged_list(os.path.join("configs", "scripts")):
        if not rel.endswith(".ltx") or "/" not in rel:
            continue
        level = rel.split("/")[0]
        if level not in LEVEL_PREFIX:
            continue
        path = merged(os.path.join("configs", "scripts", rel.replace("/", os.sep)))
        if path is None:
            continue
        secs, order = ini(path)
        if not any(s.startswith("kamp@") for s in secs):
            continue
        for name in order:
            if not name.startswith("logic@"):
                continue
            act = secs[name].get("active", "")
            reached = _reach(secs, act) if act in secs else set()
            seen_centres = set()
            for sec in reached:
                k = secs[sec]
                if not sec.startswith("kamp@") or "center_pos" not in k:
                    continue
                c = tuple(nums(k["center_pos"]))
                key = (level, "%.2f,%.2f,%.2f" % c)
                camp = out.setdefault(key, dict(level=level, key=key, centre=c, radius=float(k.get("radius", 2)), avoid=[], jobs=[], files=set(), sections={}))
                camp["radius"] = float(k.get("radius", camp["radius"]))
                camp["sections"][(path, sec)] = [tuple(nums(i)) for i in k.get("avoid", "").split("|") if len(nums(i)) == 4]
                for item in k.get("avoid", "").split("|"):
                    v = nums(item)
                    if len(v) == 4 and tuple(v) not in camp["avoid"]:
                        camp["avoid"].append(tuple(v))
                if key not in seen_centres:
                    seen_centres.add(key)
                    camp["jobs"].append((rel, name))
                    camp["files"].add(rel)
    return sorted(out.values(), key=lambda c: (c["level"], c["centre"]))


def covers():
    """smart_cover objects of the merged all.spawn: (name, pos, kind) with kind = animpoint_sit_normal / sit_high / stay_table / stay_wall."""
    sp, _ = spawn_entities()
    out = []
    for e in sp.ents:
        if e.section != "smart_cover":
            continue
        m = re.search(rb"animpoint_(?:sit_normal|sit_high|stay_table|stay_wall)", bytes(e.pk))
        out.append((e.name, e.pos, m.group(0).decode() if m else "?"))
    return out


def ensure_ai(level, ai_root):
    """path of <ai_root>\\gamedata.db0\\levels\\<level>\\level.ai; extracted from the mod archive when missing."""
    dst = os.path.join(ai_root, "gamedata.db0", "levels", level, "level.ai")
    if os.path.isfile(dst):
        return dst
    import xdb
    want = "levels\\%s\\level.ai" % level
    p = os.path.join(ADDON_UNPACKED, "gamedata.db0")
    f = open(p, "rb")
    for n, rs, cs, ptr in xdb.index(f, 0, os.path.getsize(p)):
        if n == want:
            f.seek(ptr)
            d = f.read(cs)
            if rs != cs:
                d = xdb.lzo1x(d, rs)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(d)
            return dst
    raise SystemExit("level.ai of %s not found in %s" % (level, p))


def spawn_entities():
    """(AllSpawn, patrol paths dict name -> points) of the merged all.spawn."""
    import xrspawn as X
    path = merged(SPAWN_REL)
    data = open(path, "rb").read()
    sp = X.AllSpawn(data)
    pat = X.Patrols(dict(X.chunks(data))[3])
    return sp, {p["name"]: p["points"] for p in pat.paths}


def d2(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])
