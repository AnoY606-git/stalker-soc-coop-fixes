"""Compare the qa_state.log snapshots of N co-op clients and report shared-state mismatches.   (python -I qa_compare.py ...)

  python -I qa_compare.py --log A=<A logs>\\qa_state.log --log B=<B logs>\\qa_state.log
         [--timeout 90] [--poll 3]            keep re-reading the logs until the shared state is equal (poll, never check once)
         [--require-flag NAME ...]            every client must have this story flag (reports when each client got it)
         [--expect-mismatch]                  mutation twin: PASS only if the shared state STAYS different for the whole window
         [--ignore-flags REGEX] [--ignore-infos REGEX] [--no-presence] [--out compare.json]

Categories
  SHARED   (must be identical on every client): level, story flags (story_flags table), info portions, tasks (id -> state)
  PRESENCE (cross-check): each client lists the other players in db.mp_actors, and the position it sees for them is near the
           position that player reports for itself (--presence-dist, default 25 m; positions are 5 s apart)
  PER-PLAYER (informational, never a failure): own position, health, nearby object counts by section, own player id/name
Exit 0 = PASS, 1 = FAIL, 2 = no usable data.
"""
import argparse
import json
import math
import re
import sys
import time


def last_snapshot(path):
    """Newest snapshot of the log that has spawned=true (the file is append-only, one JSON object per line)."""
    best = None
    first_spawn = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    s = json.loads(line)
                except ValueError:
                    continue
                if s.get("spawned"):
                    best = s
                    if first_spawn is None:
                        first_spawn = s
    except OSError:
        return None
    return best


def dist(a, b):
    if not a or not b:
        return None
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def shared_diff(snaps, ign_flags, ign_infos):
    """-> list of (category, detail) mismatches between the snapshots."""
    out = []
    roles = sorted(snaps)
    ref = roles[0]

    def pick(s, key):
        v = s.get("shared", {}).get(key)
        return v

    for key in ("level",):
        vals = {r: pick(snaps[r], key) for r in roles}
        if len(set(map(str, vals.values()))) > 1:
            out.append(("level", "level differs: " + ", ".join("%s=%s" % (r, vals[r]) for r in roles)))
    for key, ign in (("flags", ign_flags), ("infos", ign_infos)):
        sets = {}
        for r in roles:
            sets[r] = set(x for x in (pick(snaps[r], key) or []) if not (ign and re.search(ign, x)))
        union = set().union(*sets.values())
        for item in sorted(union):
            have = [r for r in roles if item in sets[r]]
            if len(have) != len(roles):
                miss = [r for r in roles if r not in have]
                out.append((key, "%s %s: present on %s, missing on %s" % (key[:-1], item, ",".join(have), ",".join(miss))))
    tasks = {r: (pick(snaps[r], "tasks") if isinstance(pick(snaps[r], "tasks"), dict) else {}) for r in roles}
    ids = set().union(*[set(t) for t in tasks.values()])
    for tid in sorted(ids):
        vals = {r: tasks[r].get(tid) for r in roles}
        if len(set(map(str, vals.values()))) > 1:
            out.append(("tasks", "task %s: " % tid + ", ".join("%s=%s" % (r, vals[r]) for r in roles)))
    return out


def presence_diff(snaps, max_d):
    out = []
    roles = sorted(snaps)
    for r in roles:
        others = snaps[r].get("others") or []
        want = len(roles) - 1
        if len(others) < want:
            out.append(("presence", "%s sees %d other player(s), expected %d" % (r, len(others), want)))
            continue
        for o in others:
            # find who the 'other' is: the role whose own player id matches
            peer = [q for q in roles if q != r and (snaps[q].get("player") or {}).get("id") == o.get("id")]
            if not peer:
                out.append(("presence", "%s sees player id %s that no client reports as itself" % (r, o.get("id"))))
                continue
            d = dist(o.get("pos"), (snaps[peer[0]].get("player") or {}).get("pos"))
            if d is None or d > max_d:
                out.append(("presence", "%s sees %s at %s but %s reports %s (distance %s)" % (
                    r, peer[0], o.get("pos"), peer[0], (snaps[peer[0]].get("player") or {}).get("pos"), d)))
    return out


def flag_first_seen(path, flag):
    """Seconds (harness clock) of the first snapshot that has the flag, or None."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if flag in line and line.startswith("{"):
                    try:
                        s = json.loads(line)
                    except ValueError:
                        continue
                    if flag in (s.get("shared", {}).get("flags") or []) or flag in (s.get("shared", {}).get("infos") or []):
                        return s.get("t")
    except OSError:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", required=True, help="ROLE=path to qa_state.log")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--poll", type=float, default=3)
    ap.add_argument("--require-flag", action="append", default=[])
    ap.add_argument("--expect-mismatch", action="store_true")
    ap.add_argument("--ignore-flags", default="")
    ap.add_argument("--ignore-infos", default="")
    ap.add_argument("--no-presence", action="store_true")
    ap.add_argument("--presence-dist", type=float, default=25.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    logs = dict(x.split("=", 1) for x in a.log)

    deadline = time.time() + a.timeout
    problems, snaps, polls, ever_equal = [], {}, 0, False
    while True:
        polls += 1
        snaps = {r: last_snapshot(p) for r, p in logs.items()}
        problems = []
        missing = [r for r, s in snaps.items() if s is None]
        if missing:
            problems.append(("data", "no spawned snapshot yet from client(s) " + ",".join(missing)))
        else:
            problems += shared_diff(snaps, a.ignore_flags, a.ignore_infos)
            for fl in a.require_flag:
                for r in snaps:
                    have = fl in (snaps[r]["shared"].get("flags") or []) or fl in (snaps[r]["shared"].get("infos") or [])
                    if not have:
                        problems.append(("required", "required flag %s missing on %s" % (fl, r)))
            if not a.no_presence:
                problems += presence_diff(snaps, a.presence_dist)
        if not problems:
            ever_equal = True
        if (not problems and not a.expect_mismatch) or time.time() >= deadline:
            break
        if a.expect_mismatch and ever_equal:
            break
        time.sleep(a.poll)

    # ----- report
    print("== qa_compare: %d clients, %d poll(s), window %.0f s ==" % (len(logs), polls, a.timeout))
    for r in sorted(snaps):
        s = snaps[r]
        if not s:
            print("  client %s: NO SNAPSHOT" % r)
            continue
        sh = s["shared"]
        print("  client %s (t=%.0f s, %s): level=%s flags=%d infos=%d tasks=%d" % (
            r, s.get("t", 0), s.get("side"), sh.get("level"), len(sh.get("flags") or []), len(sh.get("infos") or []), len(sh.get("tasks") or [])))
    for fl in a.require_flag:
        times = {r: flag_first_seen(p, fl) for r, p in logs.items()}
        print("  flag %s first seen (harness seconds): %s" % (fl, ", ".join("%s=%s" % (r, t) for r, t in sorted(times.items()))))
    print("SHARED STATE (must match on all clients):")
    sh_probs = [p for p in problems if p[0] in ("level", "flags", "infos", "tasks", "required")]
    pr_probs = [p for p in problems if p[0] == "presence"]
    other = [p for p in problems if p[0] == "data"]
    for p in sh_probs:
        print("  MISMATCH [%s] %s" % p)
    if not sh_probs and not other:
        print("  equal (level, %d flags, %d infos, %d tasks)" % tuple(
            len(snaps[sorted(snaps)[0]]["shared"].get(k) or []) for k in ("flags", "infos", "tasks")))
    print("PRESENCE (each client sees the others, positions agree):")
    for p in pr_probs:
        print("  MISMATCH [%s] %s" % p)
    if not pr_probs and not other and not a.no_presence:
        print("  ok")
    for p in other:
        print("  PROBLEM %s" % p[1])
    print("PER-PLAYER (informational):")
    for r in sorted(snaps):
        s = snaps[r]
        if s and s.get("player"):
            pl = s["player"]
            print("  %s: id=%s pos=%s health=%s near_total=%s sees_others=%s" % (
                r, pl.get("id"), pl.get("pos"), pl.get("health"), s.get("near_total"),
                [(o.get("name"), o.get("pos")) for o in s.get("others", [])]))

    bad = bool(problems)
    if a.expect_mismatch:
        detected = bool(sh_probs) and not ever_equal
        verdict = "PASS" if detected else "FAIL"
        print("COMPARE RESULT: %s (mutation twin: shared-state mismatch %s)" % (verdict, "detected" if detected else "NOT detected"))
        code = 0 if detected else 1
    else:
        verdict = "FAIL" if bad else "PASS"
        print("COMPARE RESULT: %s%s" % (verdict, "" if not bad else " (%d problem(s))" % len(problems)))
        code = 1 if bad else 0
    if any(p[0] == "data" for p in problems) and not a.expect_mismatch:
        code = 2 if code else code
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"verdict": verdict, "problems": problems, "snapshots": snaps}, f, indent=1)
    return code


if __name__ == "__main__":
    sys.exit(main())
