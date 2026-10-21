"""FOSTER 2026-10-21: "the trade grid is too light, and the middle of the trade window kept the old style".

- the four trade lists (dragdrop_actor_trade, dragdrop_actor_trade_bag, dragdrop_partner_trade, dragdrop_partner_bag) get a low cell
  alpha (a="GRID_A"), the attribute the same file already uses with a="0" to hide the belt / slot cells: a dark, faint SoC-like grid;
- the centre column (main: ui_inGame2_inventory_back) is tinted to the rust brown of the SoC panels. Its art carries the slot boxes and the
  engine shares it with the inventory window, so it is tinted, not replaced (the inventory gets the same SoC colour).
Idempotent. usage: python darker_grid.py <patch gamedata\\configs\\ui folder>
"""
import os
import re
import sys

GRID_A = 90
TINT = 'r="196" g="164" b="122"'
LISTS = ("dragdrop_actor_trade", "dragdrop_actor_trade_bag", "dragdrop_partner_trade", "dragdrop_partner_bag")


def fix(p):
    t = open(p, "rb").read().decode("utf-8")
    n0 = t
    for name in LISTS:
        # the list node spans several lines and ends with "/>"
        m = re.search(r"<%s\b[^>]*?/>" % name, t, flags=re.S)
        if not m:
            raise SystemExit("%s: %s not found" % (p, name))
        node = m.group(0)
        if re.search(r'\sa="\d+"', node):
            new = re.sub(r'\sa="\d+"', ' a="%d"' % GRID_A, node)
        else:
            new = node[:-2].rstrip() + ' a="%d"/>' % GRID_A
        t = t.replace(node, new, 1)
    t = t.replace("<texture>ui_inGame2_inventory_back</texture>", "<texture %s>ui_inGame2_inventory_back</texture>" % TINT, 1)
    if t != n0:
        open(p, "wb").write(t.encode("utf-8"))
        print("fixed", p)
    else:
        print("unchanged", p)


if __name__ == "__main__":
    for f in ("actor_menu.xml", "actor_menu_4x3.xml"):
        fix(os.path.join(sys.argv[1], f))
