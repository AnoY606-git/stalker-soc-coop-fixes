"""Offline border check of the job sites in coop_repeat_quests.ltx (no game needed).
python check_sites.py --ai-dir <dir with esc.ai bar.ai yan.ai> [--spawn <all.spawn>] [--ltx <coop_repeat_quests.ltx>] [--selftest]

The AI map of a level reaches far beyond the playable area (Cordon: the whole bounding box), so "a node of the AI map" is not enough: FOSTER's v1.4
report showed job bandits outside the barbed wire. The playable area is rebuilt like this:
  - nodes with less than CLEAR m to a missing node are dropped (fence lines are one node wide gaps; the outside world is linked to the fenced area only
    through such narrow leaks). Cordon uses 2.5 m, which also separates the part south of the army checkpoint (its barrier is a wall of gaps)
  - 40 m around every level changer are cut (beyond it is the next level)
  - the component holding the hub (where the players live) is the playable area; a site must lie in it and at least MIN_OUT m from its exterior
Every site of every job (kill, camp, defend, find) must pass. --selftest runs the same code on the old (v1.4) sites and requires them to FAIL.
Exit code 1 when a site is outside."""
import os, re, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "soc_levels", "tools"))
import xrspawn
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt, binary_dilation, label

AIF = {"coop_l01_escape": "esc.ai", "coop_l05_bar": "bar.ai", "coop_l08_yantar": "yan.ai"}
HUB = {"coop_l01_escape": (-199, -20, -136), "coop_l05_bar": (130, 0, 60), "coop_l08_yantar": (34, -12, -277)}
CLEAR = {"coop_l01_escape": 2.5, "coop_l05_bar": 0.0, "coop_l08_yantar": 0.0}
MIN_OUT = {"coop_l01_escape": 25.0, "coop_l05_bar": 6.0, "coop_l08_yantar": 6.0}
CUT = 40.0
# v1.4 sites that were outside (node id of the level, name): the checker must reject all of them
OLD_BAD = {
    "coop_l01_escape": {"rq_sid_camp": 1178392, "rq_sid_kill (south of the army checkpoint)": 551093, "rq_sid_defend": 152059, "rq_wolf_camp1": 393820},
    "coop_l05_bar": {"rq_ska_kill (beyond the exits)": 83, "rq_bar_kill1 (beyond the exits)": 6319, "rq_vor_kill (beyond the exits)": 22101},
    "coop_l08_yantar": {"rq_sak_camp2 (beyond the exit)": 141440},
}


def level_changers(spawn, level):
    a = xrspawn.AllSpawn(open(spawn, "rb").read())
    g = a.graph
    lid = [l["id"] for l in g.levels if l["name"] == level][0]
    out = []
    for e in a.ents:
        if e.section == "level_changer" and e.gvid < g.vc and int(g.verts["lw"][e.gvid] & 0xff) == lid:
            out.append(e.pos)
    return out


def playable(level, ai_dir, spawn):
    ai = xrspawn.LevelAI(os.path.join(ai_dir, AIF[level]))
    L = ai.links()
    nx, nz = int(ai.xi.max()) + 1, int(ai.zi.max()) + 1
    has = np.zeros((nx, nz), dtype=bool)
    has[ai.xi, ai.zi] = True
    cl = (distance_transform_edt(has) * ai.size)[ai.xi, ai.zi]
    keep = cl >= CLEAR[level] if CLEAR[level] > 0 else np.ones(ai.count, dtype=bool)
    tree = cKDTree(np.column_stack([ai.x, ai.y, ai.z]))
    for c in level_changers(spawn, level):
        keep[tree.query_ball_point(c, CUT)] = False
    src_i = np.repeat(np.arange(ai.count), 4)
    dst = L.reshape(-1)
    m = dst >= 0
    m &= keep[src_i] & keep[np.where(dst >= 0, dst, 0)]
    gm = coo_matrix((np.ones(m.sum(), dtype=np.int8), (src_i[m], dst[m])), shape=(ai.count, ai.count))
    _, lab = connected_components(gm, directed=False)
    idx = [i for i in tree.query_ball_point(HUB[level], 40) if keep[i]]
    s = idx[int(np.argmax(cl[idx]))]
    mask = (lab == lab[s]) & keep
    area = np.zeros((nx, nz), dtype=bool)
    area[ai.xi[mask], ai.zi[mask]] = True
    area = binary_dilation(area, iterations=5)
    comp, n = label(~area)
    ext = np.zeros(n + 1, dtype=bool)
    for edge in (comp[0, :], comp[-1, :], comp[:, 0], comp[:, -1]):
        ext[np.unique(edge)] = True
    ext[0] = False
    od = distance_transform_edt(~ext[comp]) * ai.size
    return ai, mask, od[ai.xi, ai.zi]


def read_sites(ltx):
    text = open(ltx, "rb").read().decode("cp1251").replace("\r\n", "\n")
    sites, cur = {}, None
    for ln in text.split("\n"):
        m = re.match(r"\[(rq_\w+)\]", ln)
        if m:
            cur = {"id": m.group(1)}
            continue
        if cur is None or "=" not in ln or ln.lstrip().startswith(";"):
            continue
        k, v = [x.strip() for x in ln.split("=", 1)]
        cur[k] = v
        if k == "site":
            sites[cur["id"]] = (cur.get("level"), [float(x) for x in re.findall(r"[-\d.]+", v)])
    # the level line comes before the site line in every section; re-read levels for safety
    cur = None
    for ln in text.split("\n"):
        m = re.match(r"\[(rq_\w+)\]", ln)
        if m:
            cur = m.group(1)
        elif cur in sites and ln.startswith("level"):
            sites[cur] = (ln.split("=", 1)[1].strip(), sites[cur][1])
    return sites


def main():
    a = sys.argv[1:]
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    ai_dir = opt("--ai-dir")
    if ai_dir is None:
        print(__doc__)
        return 2
    spawn = opt("--spawn", os.path.join(HERE, "..", "..", "darkvalley_restore", "gamedata", "spawns", "all.spawn"))
    ltx = opt("--ltx", os.path.join(HERE, "..", "gamedata", "configs", "misc", "coop_repeat_quests.ltx"))
    sites = read_sites(ltx)
    bad = 0
    for level in AIF:
        ai, mask, od = playable(level, ai_dir, spawn)
        print("%s: playable %d of %d nodes" % (level, int(mask.sum()), ai.count))
        if "--selftest" in a:
            for name, node in OLD_BAD[level].items():
                ok = bool(mask[node]) and od[node] >= MIN_OUT[level]
                print("  old %-48s %s" % (name, "ACCEPTED (checker is blind)" if ok else "rejected as expected"))
                bad += 1 if ok else 0
            continue
        for jid, (lv, v) in sites.items():
            if lv != level:
                continue
            node = int(v[3])
            if abs(ai.x[node] - v[0]) > 1.5 or abs(ai.z[node] - v[2]) > 1.5:
                print("  %-14s FAIL level vertex %d is not at the site position" % (jid, node))
                bad += 1
                continue
            ok = bool(mask[node]) and od[node] >= MIN_OUT[level]
            print("  %-14s %s inside=%s %.0f m from the border (min %.0f)" % (jid, "ok  " if ok else "FAIL", bool(mask[node]), od[node], MIN_OUT[level]))
            bad += 0 if ok else 1
    print("RESULT:", "PASS" if bad == 0 else "FAIL (%d)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
