"""Offline consistency check of the cordon_bridge patch (seconds, no game).

  python check_bridge.py [--spawn <all.spawn>]        default: patches\\darkvalley_restore\\gamedata\\spawns\\all.spawn

Checks (exit code 1 on any problem):
  * squads of esc_smart_terrain_7 in squad_descr_coop_l01_escape.ltx: members and spawn_point paths exist in all.spawn
  * the military members (sim_default_military_0) of those squads are as many as the army_N jobs; Kuznetsov has his own squad and job
  * every job in smart\\esc_smart_terrain_7.ltx has a [logic@job] section in the file it points to, with active/suitable/prior,
    on_hit / on_death in the LOGIC section (not in a walker section: the engine ignores them there) and existing target sections
  * every walker section: path_walk / path_look exist in all.spawn, every on_info target section exists, the attack twin exists
  * the hit@ / death@ sections exist in each job file and use hit_by_actor / killed_by_actor
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
CFG = os.path.join(PATCH, "gamedata", "configs")
SPAWN = os.path.join(PATCH, "..", "darkvalley_restore", "gamedata", "spawns", "all.spawn")
if "--spawn" in sys.argv:
    SPAWN = sys.argv[sys.argv.index("--spawn") + 1]
sys.path.insert(0, os.path.join(PATCH, "..", "soc_levels", "tools"))
import xrspawn as X  # noqa: E402

problems = []


def bad(msg):
    problems.append(msg)
    print("  BAD  " + msg)


def ini(path):
    secs, order, cur = {}, [], None
    for raw in open(path, "rb").read().decode("cp1251", "replace").splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            cur = m.group(1).strip()
            secs[cur] = {}
            order.append(cur)
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            secs[cur][k.strip()] = v.strip()
        elif cur is not None:
            secs[cur][line] = ""
    return secs


paths = {p["name"] for p in X.Patrols(dict(X.chunks(open(SPAWN, "rb").read()))[3]).paths}
print("all.spawn: %d patrol paths (%s)" % (len(paths), os.path.normpath(SPAWN)))

# ---- squads
sq = ini(os.path.join(CFG, "misc", "squad_descr_coop_l01_escape.ltx"))
sq = {k.split("]")[0]: v for k, v in sq.items()}
bridge = {k: v for k, v in sq.items() if v.get("target_smart") == "esc_smart_terrain_7"}
military = 0
for name, v in sorted(bridge.items()):
    members = [m.strip() for m in v.get("npc", "").split(",")]
    sp = v.get("spawn_point")
    print("squad %-44s members %s spawn_point %s story_id %s" % (name, ",".join(members), sp, v.get("story_id")))
    if sp and sp not in paths:
        bad("squad %s: spawn_point path %s is not in all.spawn" % (name, sp))
    if v.get("story_id") != name:
        bad("squad %s: story_id differs from the section name" % name)
    military += sum(1 for m in members if m == "sim_default_military_0")
print("military members in bridge squads: %d" % military)

# ---- smart terrain jobs
smart = ini(os.path.join(CFG, "scripts", "coop_l01_escape", "smart", "esc_smart_terrain_7.ltx"))
jobs = smart["exclusive"]
print("jobs: %s" % ", ".join(jobs))
army_jobs = [j for j in jobs if re.match(r"esc_smart_terrain_7_walker_army_\d+$", j)]
if len(army_jobs) != military:
    bad("%d army jobs but %d military squad members" % (len(army_jobs), military))
if "esc_smart_terrain_7_walker_kuznetsov" not in jobs or "esc_smart_terrain_7_military_kuznetsov_squad" not in bridge:
    bad("Kuznetsov job or squad missing")

cache = {}
for job, rel in jobs.items():
    f = os.path.join(CFG, "scripts", rel.replace("\\", os.sep))
    if not os.path.isfile(f):
        bad("job %s: file %s is not in the patch" % (job, rel))
        continue
    s = cache.setdefault(f, ini(f))
    lg = s.get("logic@" + job)
    if lg is None:
        bad("job %s: no [logic@%s] in %s" % (job, job, rel))
        continue
    for k in ("active", "suitable", "prior", "on_hit", "on_death"):
        if k not in lg:
            bad("job %s: [logic@...] has no %s" % (job, k))
    for k in ("on_hit", "on_death"):
        t = lg.get(k)
        if t and t not in s:
            bad("job %s: %s -> [%s] does not exist in %s" % (job, k, t, rel))
    act = lg.get("active", "")
    w = s.get(act)
    if w is None:
        bad("job %s: active section %s missing" % (job, act))
        continue
    for k in w:
        if k in ("on_hit", "on_death"):
            bad("job %s: %s sits in [%s]: the engine reads it only from [logic@...]" % (job, k, act))
    # every walker section of the job: paths and switch targets
    for sec in [act, act + "_attack_players"]:
        w = s.get(sec)
        if w is None:
            bad("job %s: section %s missing" % (job, sec))
            continue
        for k in ("path_walk", "path_look"):
            if w.get(k) is None:
                bad("%s: no %s" % (sec, k))
            elif w[k].startswith("walker_") or w[k].startswith("esc_"):
                full = "esc_smart_terrain_7_" + w[k] if not w[k].startswith("esc_") else w[k]
                if full not in paths:
                    bad("%s: %s -> path %s is not in all.spawn" % (sec, k, full))
        for k, v in w.items():
            if k.startswith("on_info"):
                m = re.search(r"\}\s*(\S+)", v)
                if m and m.group(1) not in s:
                    bad("%s: %s switches to missing section %s" % (sec, k, m.group(1)))
        hostile = sec.endswith("_attack_players")
        if w.get("combat_ignore_cond") != ("false" if hostile else "true"):
            bad("%s: combat_ignore_cond is %s" % (sec, w.get("combat_ignore_cond")))

for f, s in cache.items():
    rel = os.path.relpath(f, CFG)
    for sec, cond in (("hit@esc_bridge_soldier", "hit_by_actor"), ("death@esc_bridge_soldier", "killed_by_actor")):
        v = s.get(sec, {}).get("on_info", "")
        if "=" + cond not in v or "+ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO" not in v or "-ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO" not in v:
            bad("%s: [%s] on_info is not the player-only, once-only order rule: %s" % (rel, sec, v))

print("%d problem(s)" % len(problems))
sys.exit(1 if problems else 0)
