"""Collects the original SoC texts of the artifact / mutant part orders into tools/fetch_texts.json (read by gen_fetch.py).
Run once (the result is committed, gen_fetch.py needs no game files):

  python -I soc_fetch_texts.py --eng <stable_task_manager.xml> --rus <st_soc_strings.xml>

--eng  the Steam SoC English file  config\\text\\eng\\stable_task_manager.xml  (windows-1252), made with
       python -I tools\\xdb_soc.py "text.eng.stable_task_manager" x <outdir>
--rus  the original Russian SoC string file  configs\\text\\rus\\st_soc_strings.xml  (windows-1251, from shadow_of_chernobyl.addon via tools\\xdb.py)
Per SoC task <id> the strings are: <id> (title = menu option and PDA name), <id>_text (what the giver says), <id>_descr (PDA description);
shared ones: tm_seek_job_yes (accept), tm_reward_job (hand-in line), tm_<parent>_job_ask / tm_<parent>_job_complete (giver lines)."""
import json
import os
import re
import sys


def load(path, enc):
    t = open(path, "rb").read().decode(enc)
    return {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in re.finditer(r'<string id="([^"]+)">\s*<text>(.*?)</text>', t, re.S)}


def main():
    a = sys.argv
    eng = load(a[a.index("--eng") + 1], "cp1252")
    rus = load(a[a.index("--rus") + 1], "cp1251")
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import gen_fetch
    ids = set()
    for j in gen_fetch.JOBS:
        for s in ("", "_text", "_descr"):
            ids.add(j["soc"] + s)
    parents = sorted(set(g["parent"] for g in gen_fetch.GIVERS.values()))
    for p in parents:
        ids.update(["tm_%s_job_ask" % p, "tm_%s_job_complete" % p])
    ids.update(["tm_seek_job_yes", "tm_reward_job"])
    out = {"eng": {}, "rus": {}}
    bad = []
    for i in sorted(ids):
        if i not in eng or i not in rus:
            bad.append(i)
            continue
        out["eng"][i] = eng[i]
        out["rus"][i] = rus[i]
    if bad:
        print("missing in the sources:", bad)
        sys.exit(1)
    p = os.path.join(here, "fetch_texts.json")
    json.dump(out, open(p, "w", encoding="ascii"), indent=0, sort_keys=True)
    print("wrote %s: %d ids per language" % (p, len(ids)))


if __name__ == "__main__":
    main()
