"""Add the items each original SoC trader stocked that the mod's lists lack (owner 2026-10-22: "add what is native").
SoC lists: Steam SoC 1.0006 config\\misc\\trade_trader / trade_barman / trade_dolg / trade_freedom.ltx (all supplies stages merged).
Only missing sections are added to [supplies_start] (count as in SoC, chance 1); ammo lines also go to [supplies_start_ammo]
(the per-player ammo top-up copy, see NOTES section B). Existing stock lines are never changed. Idempotent.
A stocked item is only sold when [trade_generic_sell] prices it (a missing or ";NO TRADE" line means the trader never sells it),
so every added item, and every item in PRICE, gets a sell line when it has none or ";NO TRADE", and a buy line (players sell it back)
only when it has no buy line at all (a ";NO TRADE" buy line is the mod's choice and stays).
SoC killer_outfit does not exist in this mod (its mercenary suit is merc_outfit, which the Barman already stocks), so it is not added
and an earlier killer_outfit stock line is removed (DROP).
usage: python add_soc_stock.py <patch gamedata\\configs\\misc\\trade folder>
"""
import os
import re
import sys

ADD = {
    "esc_smart_terrain_1_trader_sidorovich.ltx": [("ammo_9x18_pmm", 10),
                                                  # not SoC: maintainer request 2026-10-22 (white leather jacket)
                                                  ("white_novice_outfit", 3)],
    "bar_smart_terrain_1_trader_barman.ltx": [("wpn_pb", 3), ("wpn_colt1911", 3), ("wpn_l85", 3), ("wpn_sig550", 3), ("wpn_g36", 3),
                                              ("ammo_5.56x45_ss190", 15)],
    "bar_smart_terrain_4_duty_petrenko.ltx": [("wpn_walther", 3), ("wpn_sig220", 3), ("wpn_ak74u", 3), ("wpn_val", 2), ("wpn_svd", 2),
                                              ("ammo_11.43x23_hydro", 10)],
    "mil_smart_terrain_2_trader_miser.ltx": [("wpn_g36", 3), ("exo_outfit", 2)],
}
# stocked by the mod but never priced, so never sold (maintainer request 2026-10-22: leather coat at Sidorovich)
PRICE = {
    "esc_smart_terrain_1_trader_sidorovich.ltx": ["black_coat_outfit"],
}
DROP = {
    "bar_smart_terrain_1_trader_barman.ltx": ["killer_outfit"],
}
BUY = "0.6, 0.6"
SELL = "2, 3"
SELL_AMMO = "2, 2"


def section_body(t, name):
    return re.search(r"(?ms)^\[%s\][^\n]*\n(.*?)(?=^\[|\Z)" % re.escape(name), t)


def key(line):
    return line.split(";")[0].split("=")[0].strip()


def add(t, sec, lines, nl):
    m = section_body(t, sec)
    if not m:
        return t, 0
    body = m.group(1)
    have = set(key(l) for l in body.split(nl) if "=" in l.split(";")[0])
    new = [l for l in lines if key(l) not in have]
    if not new:
        return t, 0
    ins = "".join("%s%s" % (l, nl) for l in new)
    body2 = body.rstrip() + nl + ";-- original SoC stock (patch soc_economy, add_soc_stock.py)" + nl + ins + nl
    return t[:m.start(1)] + body2 + t[m.end(1):], len(new)


def drop(t, sec, names, nl):
    m = section_body(t, sec)
    if not m:
        return t, 0
    rows = m.group(1).split(nl)
    keep = [l for l in rows if key(l) not in names]
    return t[:m.start(1)] + nl.join(keep) + t[m.end(1):], len(rows) - len(keep)


def price(t, sec, item, value, nl, replace_no_trade=True):
    """Give item a price line in sec: replace a ';NO TRADE' line (sell list only), or append when there is no line."""
    m = section_body(t, sec)
    if not m:
        return t, 0
    rows = m.group(1).split(nl)
    line = "%-40s= %s" % (item, value)
    for i, l in enumerate(rows):
        if key(l) == item:
            if "=" in l.split(";")[0] or not replace_no_trade:
                return t, 0
            rows[i] = line
            return t[:m.start(1)] + nl.join(rows) + t[m.end(1):], 1
    body = m.group(1).rstrip() + nl + line + nl + nl
    return t[:m.start(1)] + body + t[m.end(1):], 1


def main():
    d = sys.argv[1]
    for fn in sorted(set(ADD) | set(PRICE) | set(DROP)):
        items = ADD.get(fn, [])
        p = os.path.join(d, fn)
        t = open(p, "rb").read().decode("latin-1")
        nl = "\r\n" if "\r\n" in t else "\n"
        lines = ["%-40s= %d, 1" % (s, c) for s, c in items]
        t, a = add(t, "supplies_start", lines, nl)
        ammo = [l for l in lines if l.startswith("ammo_")]
        b = 0
        if ammo:
            t, b = add(t, "supplies_start_ammo", ammo, nl)
        r = 0
        for sec in ("supplies_start", "supplies_start_ammo"):
            t, n = drop(t, sec, DROP.get(fn, []), nl)
            r += n
        pr = 0
        for s in [s for s, _ in items] + PRICE.get(fn, []):
            t, n1 = price(t, "trade_generic_sell", s, SELL_AMMO if s.startswith("ammo_") else SELL, nl)
            t, n2 = price(t, "trade_generic_buy", s, BUY, nl, replace_no_trade=False)
            pr += n1 + n2
        open(p, "wb").write(t.encode("latin-1"))
        print(fn, "added", a, "supplies lines,", b, "ammo copy lines,", pr, "price lines, removed", r)


if __name__ == "__main__":
    main()
