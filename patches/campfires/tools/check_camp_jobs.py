"""Offline check (no game, seconds): job slots versus stalkers per smart terrain, for every smart terrain that has a campfire (kamp) job.

  python check_camp_jobs.py [--smart esc_smart_terrain_1 ...] [--players 4]     exit code 1 on any BAD line

Why: every NPC that a smart terrain holds needs a job (smart_terrain.script select_npc_job: no job = abort / a stalker that stands where he spawned).
The jobs of a smart terrain are what gulag_general.load_job builds (read from the merged tree = what build.py ships, see camp_lib.py):
  * exclusive jobs of smart\\<smart>.ltx [exclusive] (a job with `suitable = {=check_npc_name(x)}` is only for that named stalker);
  * 20 `point` jobs (cover scheme, prior 3) that every smart terrain has: the last resort that makes "no job" practically impossible;
  * one job per patrol path <smart>_<kind>_<N>_walk (kind guard / walker / patrol / collector / sniper / camper; surge and sleep are
    time/event bound and not counted), N counted up from 1 without a gap, like the Lua loop;
  * one job per smart_cover <smart>_animpoint_<N> that is not listed in skip_animpoints of the smart terrain ini.
Population = squads of the smart in [start_position_<level>] of simulation.ltx (members from squad_descr), plus squads that a script can create
there later (named in a create_squad effect), plus the roaming cap (alife_roaming.ltx max_npc_per_smart) when the smart is in a roaming group.
Enemy scaling (player_scaling.ltx) only grows squads of hostile factions; the human camp dwellers are listed with their factor.
BAD: peak population of humans larger than the unnamed job slots, a named stalker without his own job, an exclusive job file or section missing,
a kamp job that names no existing section.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camp_lib as C  # noqa: E402

args = sys.argv[1:]
players = 4
if "--players" in args:
    players = int(args[args.index("--players") + 1])
only = [args[i + 1] for i, a in enumerate(args) if a == "--smart"]

HUMAN = {"stalker", "bandit", "dolg", "freedom", "army", "ecolog", "killer", "military", "zombied", "monolith"}
PATH_KINDS = ("walker", "patrol", "collector", "guard", "sniper", "camper")


def read(rel):
    p = C.merged(rel)
    return C.ini(p) if p else ({}, [])


sp, paths = C.spawn_entities()
covers = {e.name for e in sp.ents if e.section == "smart_cover"}

# smart terrains that have a kamp job
smarts = {}
for camp in C.camps():
    for rel, logic in camp["jobs"]:
        m = re.search(r"([a-z]+_smart_terrain_\d+)", os.path.basename(rel))
        if m:
            smarts.setdefault((camp["level"], m.group(1)), set()).add(camp["key"][1])
if only:
    smarts = {k: v for k, v in smarts.items() if k[1] in only}

ps_secs, _ = read(os.path.join("configs", "player_scaling.ltx"))
ps = ps_secs.get("player_scaling", ps_secs.get("scaling", {}))
hostile = set(re.findall(r"[a-z_]+", ps.get("hostile_factions", "")))
max_factor = float(ps.get("max_factor", 1) or 1)
extra_pp = float(ps.get("human_extra_per_player", 0.5) or 0.5)
rm_secs, _ = read(os.path.join("configs", "misc", "alife_roaming.ltx"))
roam = rm_secs.get("roaming", {})
roam_cap = int(float(roam.get("max_npc_per_smart", 99)))
roam_on = roam.get("enabled", "true") == "true"

# every text that can name a squad (for create_squad effects)
corpus = []
for sub in ("configs/scripts", "configs/gameplay", "scripts"):
    for rel in C.merged_list(sub):
        if rel.endswith((".ltx", ".xml", ".script", ".dscript")):
            p = C.merged(os.path.join(sub.replace("/", os.sep), rel.replace("/", os.sep)))
            if p:
                corpus.append((rel, open(p, "rb").read().decode("cp1251", "replace")))

bad = 0


def say(msg):
    print(msg)


for (level, smart), fires in sorted(smarts.items()):
    smart_secs, _ = read(os.path.join("configs", "scripts", level, "smart", smart + ".ltx"))
    st = smart_secs.get("smart_terrain", {})
    excl = smart_secs.get("exclusive", {})
    skip = set(int(n) for n in re.findall(r"\d+", st.get("skip_animpoints", "")))
    named_jobs, plain_jobs = {}, []
    problems = []
    for jid, rel in excl.items():
        rel = rel.replace("\\", "/")
        p = C.merged(os.path.join("configs", "scripts", rel.replace("/", os.sep)))
        if p is None:
            problems.append("exclusive job %s: file %s does not exist" % (jid, rel))
            continue
        secs, _ = C.ini(p)
        lg = secs.get("logic@" + jid)
        if lg is None or "active" not in lg:
            problems.append("exclusive job %s: no [logic@%s] with `active` in %s" % (jid, jid, rel))
            continue
        if lg["active"] not in secs:
            problems.append("exclusive job %s: active section %s missing" % (jid, lg["active"]))
        m = re.search(r"check_npc_name\(([A-Za-z_0-9]+)\)", lg.get("suitable", ""))
        if m:
            named_jobs[m.group(1)] = jid
        else:
            plain_jobs.append(jid)
    generic = {"point": 20}
    for kind in PATH_KINDS:
        n = 1
        while "%s_%s_%d_walk" % (smart, kind, n) in paths:
            n += 1
        if n > 1:
            generic[kind] = n - 1
    n, ap = 1, 0
    while "%s_animpoint_%d" % (smart, n) in covers:
        if n not in skip:
            ap += 1
        n += 1
    if ap:
        generic["animpoint"] = ap
    generic_total = sum(generic.values())

    # population
    sim, _ = read(os.path.join("configs", "misc", "simulation.ltx"))
    start = sim.get("start_position_" + level, {})
    descr, _ = read(os.path.join("configs", "misc", "squad_descr_%s.ltx" % level))
    squads = {k: v for k, v in descr.items() if v.get("target_smart") == smart}
    members = {"start": [], "later": []}
    for name, v in squads.items():
        npcs = [x.strip() for x in v.get("npc", "").split(",") if x.strip()]
        faction = v.get("faction", "")
        if faction not in HUMAN:
            continue
        where = "start" if start.get(name) == smart else None
        if where is None:
            used = any(name in txt for rel, txt in corpus if not rel.startswith("misc/"))
            where = "later" if used else None
        if where:
            members[where].append((name, faction, npcs))
    start_n = sum(len(n) for _, _, n in members["start"])
    later_n = sum(len(n) for _, _, n in members["later"])
    hostile_here = [f for _, f, _ in members["start"] + members["later"] if f in hostile]
    factor = min(max_factor, 1 + extra_pp * (players - 1)) if hostile_here else 1.0
    peak = int(start_n * (factor if hostile_here else 1)) + later_n
    in_roam = roam_on and re.search(r"\b%s\b" % smart, " ".join(v.get("group_stalker", "") + " " + v.get("group_bandit", "") for k, v in
                                                                 read(os.path.join("configs", "misc", "alife_roaming.ltx"))[0].items() if k.startswith("level@" + level)))
    if in_roam:
        peak = max(peak, roam_cap)
    named_members = [n for _, _, ns in members["start"] + members["later"] for n in ns if not n.startswith("sim_default")]
    plain_members = peak - len([n for n in named_members])
    say("%s (%s), fires %s" % (smart, level, ", ".join(sorted(fires))))
    say("   jobs: %d named (%s), %d unnamed exclusive (%s), generic %d (%s)" % (
        len(named_jobs), ", ".join(sorted(named_jobs.values())) or "-", len(plain_jobs), ", ".join(plain_jobs) or "-", generic_total,
        ", ".join("%s %d" % kv for kv in sorted(generic.items())) + ("; skipped covers %s" % sorted(skip) if skip else "")))
    say("   max_population %s (squads), humans: %d at start (%s), %d later (%s), roaming cap %s, enemy scaling x%.1f -> peak %d"
        % (st.get("max_population", "?"), start_n, ", ".join("%s %d" % (n.replace(smart + "_", ""), len(m)) for n, _, m in members["start"]) or "-",
           later_n, ", ".join("%s %d" % (n.replace(smart + "_", ""), len(m)) for n, _, m in members["later"]) or "-",
           roam_cap if in_roam else "no roaming", factor, peak))
    for nm in named_members:
        if nm not in named_jobs:
            say("   note: named stalker %s has no exclusive job of his own here (he takes a generic one)" % nm)
    free = len(plain_jobs) + generic_total
    unnamed = peak - len([n for n in named_members if n in named_jobs])
    ok = unnamed <= free
    say("   unnamed slots %d (%d exclusive + %d generic) for %d stalkers: %s" % (free, len(plain_jobs), generic_total, unnamed, "OK" if ok else "BAD not enough jobs"))
    for pr in problems:
        say("   BAD " + pr)
    bad += (0 if ok else 1) + len(problems)
    say("")

say("%d problem(s)" % bad)
sys.exit(1 if bad else 0)
