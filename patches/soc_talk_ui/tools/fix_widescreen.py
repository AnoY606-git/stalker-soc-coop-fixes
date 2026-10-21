"""16:9 talk window: undo the horizontal stretch and drop the shade stripes (FOSTER, 2026-10-21).

The first version scaled the SoC layout 1920/1024 wide but 1080/768 high, so the 600 px SoC frame art came out 4/3 too wide
("the dialog window looks stretched"). The frames and lists are now 600 * 1080/768 = 844 px wide, centred. The top / bottom
shade stripes (ui_top_background / ui_bottom_background) are removed; their nodes stay (size 0, no texture) because the
script creates them by name. Idempotent: it only runs on the original numbers (frames at x=409).

usage: python fix_widescreen.py <patch gamedata\\configs\\ui folder>
"""
import os
import re
import sys

K = 0.75            # undo the extra 4/3
X0, NX0 = 409, 538  # old and new left edge of the frames (new = centred, 844 wide)
CHILD = ("num_text", "name_caption", "content_text", "msg_icon")
ITEMS = ("question_item", "other_answer_item", "actor_answer_item", "iconed_answer_item", "simple_answer_item", "iconed_trade_info")


def fx(x):
    return int(round(NX0 + (x - X0) * K))


def fw(w):
    return int(round(w * K))


def scale(line, xpos):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        if k == "x" and xpos:
            v = fx(v)
        elif k == "width":
            v = fw(v)
        return '%s="%d"' % (k, v)
    return re.sub(r'\b(x|width)="(\d+)"', rep, line)


def tag(s):
    m = re.match(r"<(\w+)", s)
    return m.group(1) if m else ""


def fix_talk(p):
    t = open(p, encoding="utf-8").read()
    if 'answers_bcg x="409"' not in t:
        print("talk.xml already fixed")
        return
    out = []
    for ln in t.split("\n"):
        n = tag(ln.strip())
        if n in ("answers_bcg", "auto_static", "answers_list", "questions_list"):
            ln = scale(ln, True)
        elif n in ITEMS:
            ln = scale(ln, False)
        elif n in CHILD:
            ln = re.sub(r'\bwidth="(\d+)"', lambda m: 'width="%d"' % (fw(int(m.group(1))) if int(m.group(1)) > 200 else int(m.group(1))), ln)
        out.append(ln)
    open(p, "w", encoding="utf-8", newline="").write("\n".join(out))
    print("talk.xml fixed")


def fix_info(p):
    t = open(p, encoding="utf-8").read()
    if 'header1 x="409"' not in t:
        print("soc_talk_info.xml already fixed")
        return
    out = []
    for ln in t.split("\n"):
        s = ln.strip()
        n = tag(s)
        if n in ("header1", "header2", "title_npc", "title_actor"):
            ln = scale(ln, True)
        elif n in ("top_bg", "bot_bg"):
            ln = re.sub(r'\b(width|height)="\d+"', r'\1="0"', ln)
        elif s in ("<texture>ui\\ui_top_background</texture>", "<texture>ui\\ui_bottom_background</texture>"):
            ln = ln.replace(s, "<!-- shade stripe removed (FOSTER); the node stays because the script creates it by name -->")
        out.append(ln)
    open(p, "w", encoding="utf-8", newline="").write("\n".join(out))
    print("soc_talk_info.xml fixed")


if __name__ == "__main__":
    d = sys.argv[1]
    fix_talk(os.path.join(d, "talk.xml"))
    fix_info(os.path.join(d, "soc_talk_info.xml"))
