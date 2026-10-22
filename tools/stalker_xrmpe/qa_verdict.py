r"""The REAL outcome of a run_coop.ps1 result folder (run_coop prints RESULT: FAIL for harmless harness noise).

  python tools\stalker_xrmpe\qa_verdict.py <ResultDir> [--prefix NA]  [--require N]

Reads <ResultDir>\run.log, compare.json and every client_*\qa_assert.log (the dedicated server's asserts live in client_S) and prints
  - the assert counts and every FAIL line (optionally only those whose name starts with --prefix),
  - the compare problems, split into KNOWN NOISE (after a respawn or level change the comparer reports "A sees player id N that no client
    reports as itself": a presence mismatch, not a bug) and REAL problems (shared state differs, level differs, ...),
  - FAILURE lines of run_coop (a client crash, no spawn).
Verdict PASS = all clients spawned, no FAILURE line, no FAIL assert, no real compare problem (and at least --require PASS asserts when given).
Exit code 0 on PASS, 1 on FAIL, 2 when the folder has no usable files.  A result folder that holds only an empty run (queued, no run.log yet)
reports QUEUED/EMPTY: check the slot queue with  python tools\stalker_xrmpe\stalker_slot.py status.
"""
import argparse
import glob
import json
import os
import re
import sys


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_dir")
    ap.add_argument("--prefix", default="", help="only count asserts whose name starts with this (for example NA or RG)")
    ap.add_argument("--require", type=int, default=0, help="at least this many PASS asserts are needed")
    a = ap.parse_args()
    d = a.result_dir
    if not os.path.isdir(d):
        print("no such folder: " + d)
        return 2
    run = read(os.path.join(d, "run.log"))
    if run is None:
        n = len(os.listdir(d))
        print("QUEUED/EMPTY: no run.log in %s (%d file(s)). run_coop writes run.log only after it got a slot lease; "
              "check:  python tools\\stalker_xrmpe\\stalker_slot.py status" % (d, n))
        return 2
    lines = run.splitlines()
    spawned = [l for l in lines if re.search(r"all \d+ clients spawned", l)]
    failure = [l for l in lines if "FAILURE:" in l]
    result = next((l for l in reversed(lines) if "RESULT:" in l), "")

    n_pass, fails = 0, []
    for p in sorted(glob.glob(os.path.join(d, "client_*", "qa_assert.log"))):
        side = os.path.basename(os.path.dirname(p))
        for ln in (read(p) or "").splitlines():
            m = re.match(r"^(PASS|FAIL) (.*)$", ln)
            if not m:
                continue
            # a crashed qa_lib task ("FAIL task <name> ...") always counts, whatever --prefix says
            task_fail = m.group(1) == "FAIL" and m.group(2).startswith("task ")
            if not task_fail and not m.group(2).startswith(a.prefix):
                continue
            if m.group(1) == "PASS":
                n_pass += 1
            else:
                fails.append("%s: %s" % (side, m.group(2)[:200]))

    noise, real = [], []
    cj = read(os.path.join(d, "compare.json"))
    if cj:
        try:
            for cat, text in json.loads(cj).get("problems", []):
                if cat == "presence" and re.search(r"sees player id \d+ that no client reports as itself", text):
                    noise.append("[%s] %s" % (cat, text))
                else:
                    real.append("[%s] %s" % (cat, text))
        except ValueError:
            real.append("compare.json unreadable")

    print("run_coop said : " + (result.split("]", 1)[-1].strip() or "(no RESULT line)")[:140])
    print("spawned       : " + (spawned[0].split("]", 1)[-1].strip() if spawned else "NO"))
    print("asserts       : %d PASS, %d FAIL%s" % (n_pass, len(fails), (" (names starting with %s)" % a.prefix) if a.prefix else ""))
    for f in fails:
        print("  FAIL " + f)
    for f in failure:
        print("  FAILURE " + f.split("]", 1)[-1].strip()[:200])
    print("compare       : %d real problem(s), %d known noise (presence after respawn / level change)" % (len(real), len(noise)))
    for r in real:
        print("  REAL " + r)
    ok = bool(spawned) and not failure and not fails and not real and n_pass >= a.require
    print("VERDICT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
