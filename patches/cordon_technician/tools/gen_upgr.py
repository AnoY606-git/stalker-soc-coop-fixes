r"""Builds gamedata/configs/misc/stalkers_upgrade_info.ltx for the Cordon technician.

The mod's own file (configs\misc\stalkers_upgrade_info.ltx from the add-on, db0) is copied byte for byte and two sections are
appended for the profile `esc_rookie_technician`:
  [esc_rookie_technician]        the items he can upgrade (the engine reads <profile> for the item list)
  [esc_rookie_technician_upgr]   `up_sect_x = false` for every upgrade whose cost is above BASIC_MAX (the mod's tier switch,
                                 read by inventory_upgrades.precondition_functor_a / prereq_functor_a as <profile>_upgr)
Costs come from the upgrade definition files (weapons\upgrades\*.ltx, misc\outfit_upgrades\*.ltx; later directories win).

usage: python gen_upgr.py <mod stalkers_upgrade_info.ltx> <out.ltx> <upgrade dir> [<upgrade dir> ...]
"""
import os, re, sys

PROFILE = "esc_rookie_technician"
BASIC_MAX = 2000

ITEMS = """
; pistols
wpn_pm
wpn_pb
wpn_fort
wpn_fort_m1
wpn_hpsa
wpn_beretta
wpn_walther
wpn_walther_m1
wpn_colt1911
; shotguns
wpn_bm16
wpn_toz34
wpn_toz34_m1
wpn_wincheaster1300
wpn_wincheaster1300_m1
; automatics
wpn_mp5
wpn_mp5_m1
wpn_ak74u
wpn_ak74u_m1
wpn_ak74
wpn_ak74_m1
wpn_abakan
wpn_abakan_m1
; rookie suits and helmets
novice_outfit
novice_outfit_anomaly
white_novice_outfit
stalker_outfit
stalker_outfit_tourist
helm_hardhat
helm_respirator
"""


def costs(dirs):
    c = {}
    for d in dirs:
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(".ltx"):
                continue
            cur = None
            for line in open(os.path.join(d, fn), "rb").read().decode("cp1251", "replace").split("\n"):
                m = re.match(r"\[(up_sect_\w+)\]", line.strip())
                if m:
                    cur = m.group(1)
                    continue
                m = re.match(r"\s*cost\s*=\s*(\d+)", line)
                if m and cur:
                    c[cur] = int(m.group(1))
                    cur = None
    return c


def main():
    src, out = sys.argv[1], sys.argv[2]
    c = costs(sys.argv[3:])
    base = open(src, "rb").read()
    text = []
    text.append("")
    text.append(";************************************************")
    text.append(";**** Cordon rookie technician (patches/cordon_technician)")
    text.append(";**** Items: common Cordon gear. No discount_condlist: base prices, same as the Bar mechanic without his faction markup.")
    text.append(";**** Upgrades: only basic ones (cost <= %d). Everything dearer is switched off below, like the mod does for the Yantar tech." % BASIC_MAX)
    text.append(";************************************************")
    text.append("")
    text.append("[%s]" % PROFILE)
    text.extend(ITEMS.strip().split("\n"))
    text.append("")
    text.append("[%s_upgr]" % PROFILE)
    n = 0
    for name in sorted(c):
        if c[name] > BASIC_MAX:
            text.append("%s = false" % name)
            n += 1
    text.append("")
    blob = ("\r\n".join(text)).encode("ascii")
    if not base.endswith(b"\r\n"):
        base += b"\r\n"
    open(out, "wb").write(base + blob)
    print("wrote", out, "upgrades total", len(c), "switched off", n, "kept", len(c) - n)


main()
