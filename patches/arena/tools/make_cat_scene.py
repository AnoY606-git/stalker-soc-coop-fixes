"""Builds the arena cat-scene restrictor from the mod's stock file (cp1251, CRLF kept).

Bug (v1.4.1 reports: "after the arena we stand staring at the wall", a player frozen in Arnie's room):
when a round ends the restrictor goes back to idle_start_cat_scene while the players are still in the
pit (the server teleports them out only 20 s later), so on_player_inside fires again, runs disable_ui
(input off, HUD hidden) and waits for START_CAT_SCENE_INFO, which was just cleared. Nothing ever runs
enable_ui again, so the player is teleported back to Arnie's room still frozen.

Fix:
- the cutscene only arms while a fight is requested and not yet running ({+START_CAT_SCENE_INFO -START_ARENA_GO});
- after a round the restrictor waits until the local player has left the zone before it can arm again;
- every way out of a disabled state runs enable_ui, and two timers make sure input can never stay off
  (5 s without the cutscene flag, 30 s for the cutscene itself).

usage: python make_cat_scene.py <mod source gamedata.db0> <out file>
"""
import re
import sys

SRC_REL = "configs/scripts/coop_l05_bar/space_restrictors/arena_arny/bar_actor_cat_scene_space_restrictor.ltx"
P = "BAR_ARNY_ARENA_SMART_TERRAIN_"


def main():
    src = open(sys.argv[1] + "/" + SRC_REL, "rb").read().decode("cp1251")
    nl = "\r\n" if "\r\n" in src else "\n"
    lines = src.split(nl)
    out = []
    section = None
    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s
        key = s.split("=", 1)[0].strip() if "=" in s and not s.startswith(";") else None
        if section == "[sr_idle@idle_start_cat_scene]" and key == "on_player_inside":
            ln = ln.replace("sr_idle@idle_start_cat_scene_idle",
                            "{+%sSTART_CAT_SCENE_INFO -%sSTART_ARENA_GO} sr_idle@idle_start_cat_scene_idle" % (P, P), 1)
        elif section == "[sr_idle@idle_start_cat_scene_dead_mutant_idle]" and key and key.startswith("on_info"):
            # back to idle only after the player left the pit, and always give control back
            ln = re.sub(r"(\s)sr_idle@idle_start_cat_scene(\s+)%", r"\1sr_idle@cat_wait_leave\2%=enable_ui ", ln, count=1)
        out.append(ln)
        if section == "[sr_idle@idle_start_cat_scene_idle]" and key == "on_info":
            out.append("on_timer = 5000 | sr_idle@idle_start_cat_scene %=enable_ui%")
        elif section == "[sr_cutscene@fly]" and key == "on_signal":
            out.append("on_timer = 30000 | sr_idle@idle_start_cat_scene_dead_mutant_idle %%=enable_ui +%sSTART_ARENA_GO%%" % P)
    text = nl.join(out).rstrip() + nl + nl
    text += ("; after a round: arm again only once the local player is out of the pit" + nl +
             "[sr_idle@cat_wait_leave]" + nl +
             "on_player_outside = sr_idle@idle_start_cat_scene %=enable_ui%" + nl)
    for need in ("on_timer = 5000", "on_timer = 30000", "cat_wait_leave %=enable_ui", "-%sSTART_ARENA_GO} sr_idle@idle_start_cat_scene_idle" % P):
        assert need in text, need
    open(sys.argv[2], "wb").write(text.encode("cp1251"))
    print("written", sys.argv[2])


if __name__ == "__main__":
    main()
