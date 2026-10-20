"""Generate patches/weapon_upgrades/gamedata from the extracted Shadow of COOP 8.0 sources.

usage: python -I gen_weapon_upgrades.py "<path to 'Shadow of COOP 8.0'>" <patch gamedata dir>
Layer order (later wins, whole files): vanilla < xrmpe_cop_addon < xrmpe_patch < coop addon (source/gamedata.db0).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ltx import load, get

B = sys.argv[1].rstrip("/\\") + "/"
OUT = sys.argv[2]
LAYERS = [B + "source_base/vanilla/configs", B + "source_base/xrmpe_cop_addon/configs",
          B + "source_base/xrmpe_patch/configs", B + "source/gamedata.db0/configs"]
NOT_WEAPON = ("WP_KNIFE", "WP_BINOC", "WP_SCOPE", "WP_SILEN", "WP_GLAUN")

ws = load(LAYERS, "weapons/weapons.ltx")
van = load(LAYERS[:1], "weapons/weapons.ltx")
ups = load(LAYERS, "item_upgrades.ltx")


def weapons():
    # weapons_unique.ltx (nimble/snag/luckygun variants, the Gauss rifle) is NOT part of the running game: those sections do not exist
    # at run time (checked in game). Shipping that file would create them half-configured, so they are left out everywhere.
    for s in ws:
        cl = get(ws, s, "class")
        if cl and cl.startswith("WP_") and cl not in NOT_WEAPON and not ws[s]["_file"].replace("\\", "/").endswith("weapons_unique.ltx"):
            yield s


def trees_of(sec):
    return [x.strip() for x in (get(ws, sec, "upgrades") or "").split(",") if x.strip()]


def tree_ok(t):
    if t not in ups:
        return False
    for e in [x.strip() for x in (get(ups, t, "elements", "") or "").split(",") if x.strip()]:
        if e not in ups or get(ups, e, "section") not in ups:
            return False
        if any(f.strip() not in ups for f in (get(ups, e, "effects") or "").split(",") if f.strip()):
            return False
    return True


# section -> (source resolver, source section).  "own" = the original CoP values (vanilla layer) of the same weapon.
DONOR = {
    "wpn_fn2000": ("van", "wpn_fn2000"), "wpn_fn2000_m1": ("van", "wpn_fn2000"), "wpn_fn2000_nimble": ("van", "wpn_fn2000"),
    "wpn_spas12": ("van", "wpn_spas12"), "wpn_spas12_nimble": ("van", "wpn_spas12"),
    "wpn_svu": ("ws", "wpn_svu_xrmpe"), "wpn_svu_nimble": ("ws", "wpn_svu_xrmpe"),
    "wpn_bm16_m1": ("ws", "wpn_bm16"), "wpn_colt1911_m1": ("ws", "wpn_colt1911"), "wpn_lr300_m1": ("ws", "wpn_lr300"),
    "wpn_sig552": ("ws", "wpn_sig550"),
    "wpn_gauss": ("ws", "wpn_svd"), "pri_a17_gauss_rifle": ("ws", "wpn_svd"),
    "wpn_rpg7": ("ws", "wpn_rgm-40"), "wpn_rg-6": ("ws", "wpn_rgm-40"),
    # sections whose tree/scheme names point at nothing
    "wpn_mp5sd": ("ws", "wpn_mp5"), "wpn_pmm": ("ws", "wpn_pm"), "wpn_fort17": ("ws", "wpn_fort"), "wpn_sig220r": ("ws", "wpn_sig220"),
}
SVU_XRMPE = "vartree_svu_sights, vartree_svu_prujina, vartree_svu_tsevie_rezina, vartree_svu_tsevie_down, vartree_svu_mag"


def donor_values(src, sec):
    if src == "van":
        return get(van, sec, "upgrades"), get(van, sec, "upgrade_scheme")
    if sec == "wpn_svu_xrmpe":
        x = load([LAYERS[2]], "weapons/weapons.ltx")
        return get(x, "wpn_svu", "upgrades"), get(x, "wpn_svu", "upgrade_scheme")
    return get(ws, sec, "upgrades"), get(ws, sec, "upgrade_scheme")


def set_key(text, section, key, value):
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    start = None
    for i, l in enumerate(lines):
        m = re.match(r"\s*\[([^\]]+)\]", l)
        if m and m.group(1).strip() == section:
            start = i
            break
    if start is None:
        raise SystemExit("section %s not found" % section)
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"\s*\[", lines[j]):
            end = j
            break
    for j in range(start + 1, end):
        if re.match(r"\s*%s\s*=" % re.escape(key), lines[j]) and not lines[j].lstrip().startswith(";"):
            lines[j] = "%s = %s" % (key, value)
            return nl.join(lines)
    last = start
    for j in range(start + 1, end):
        if lines[j].strip():
            last = j
    lines.insert(last + 1, "%s = %s" % (key, value))
    return nl.join(lines)


def read(path):
    return open(path, "rb").read().decode("latin-1")


def write(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(text.encode("latin-1"))


# ---- 1. weapon sections
edits = {}
for s in weapons():
    tr = trees_of(s)
    sch = get(ws, s, "upgrade_scheme")
    if s in DONOR:
        up, sc = donor_values(*DONOR[s])
        edits[s] = (up, sc)
    elif not tr:
        raise SystemExit("weapon %s has no upgrades and no donor entry" % s)
bysrc = {}
for s, (up, sc) in edits.items():
    f = ws[s]["_file"]
    bysrc.setdefault(f, []).append(s)
for f, secs in bysrc.items():
    text = read(f)
    for s in secs:
        up, sc = edits[s]
        text = set_key(text, s, "upgrades", up)
        text = set_key(text, s, "upgrade_scheme", sc)
    rel = f.replace("\\", "/").split("/configs/", 1)[1]
    write("configs/" + rel, text)
    print("weapons:", rel, secs)

# ---- 2. upgraded_inventory + technician item lists
allw = list(weapons())
inv_path = B + "source/gamedata.db0/configs/misc/inventory_upgrades.ltx"
inv = read(inv_path)
nl = "\r\n" if "\r\n" in inv else "\n"
have = set(l.strip() for l in inv.split(nl))
missing = [w for w in allw if w not in have]
lines = inv.split(nl)
idx = next(i for i, l in enumerate(lines) if l.strip() == "novice_outfit")
lines[idx:idx] = missing + [""]
write("configs/misc/inventory_upgrades.ltx", nl.join(lines))
print("upgraded_inventory +%d" % len(missing))

info_path = B + "source/gamedata.db0/configs/misc/stalkers_upgrade_info.ltx"
info = read(info_path)
nl = "\r\n" if "\r\n" in info else "\n"
lines = info.split(nl)
for prof in ("bar_smart_terrain_10_stalker_plyushkin", "mil_smart_terrain_11_freedom_shurup"):
    s0 = next(i for i, l in enumerate(lines) if l.strip() == "[%s]" % prof)
    e0 = next((j for j in range(s0 + 1, len(lines)) if lines[j].startswith("[")), len(lines))
    have = set(l.strip().split("=")[0].strip() for l in lines[s0:e0])
    miss = [w for w in allw if w not in have]
    last = max(j for j in range(s0, e0) if lines[j].strip().startswith("wpn_"))
    lines[last + 1:last + 1] = [""] + miss
    print("technician %s +%d weapons" % (prof, len(miss)))
write("configs/misc/stalkers_upgrade_info.ltx", nl.join(lines))
