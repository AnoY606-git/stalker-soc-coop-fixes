"""Removes the technician-parts dialogs (Bar technician Plyushkin, Army Warehouses technician Shurup and Max) and the Lua helpers.

  python strip_dialogs.py <mod source gamedata.db0 folder>

Idempotent, works in place on the files that other patches own (see NOTES.md for the list) and (re)writes the two text files of this patch
from the mod's own copy. Byte level (windows-1251 files, mixed line ends), nothing else in the files is touched.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
P = os.path.join(REPO, "patches")

DIALOG_IDS = ("what_kind_of_junk_is_needed", "hand_over_the_trash")
PREFIX = "bar_smart_terrain_10_stalker_plyushkin_"

DIALOG_XML = os.path.join(P, "quest_dialogs", "gamedata", "configs", "gameplay", "dialogs_coop_l05_bar.xml")
CHAR_FILES = [
    os.path.join(P, "repeatable_quests", "gamedata", "configs", "gameplay", "character_desc_coop_l05_bar.xml"),
    os.path.join(P, "freedom_duty", "gamedata", "configs", "gameplay", "character_desc_coop_l07_military.xml"),
]
SCRIPT = os.path.join(P, "artifact_quests", "gamedata", "scripts", "dialogs_item.script")
TEXT_OUT = os.path.join(P, "no_tech_parts", "gamedata", "configs", "text")

# greeting of Plyushkin and Shurup: it asked "brought anything?" (the parts), now a plain technician greeting
GREETING = {"eng": "Hello. Something broken?", "rus": "Здоров. Что-то сломалось?"}


def edit(path, fn):
    raw = open(path, "rb").read()
    new, n = fn(raw)
    if new != raw:
        tmp = path + ".tmp_strip"
        with open(tmp, "wb") as f:
            f.write(new)
        os.replace(tmp, path)
    print("%-60s removed %d" % (os.path.relpath(path, REPO), n))


def strip_dialogs(raw):
    pat = re.compile(rb'[ \t]*<dialog id="' + PREFIX.encode() + rb'(?:' + b"|".join(d.encode() for d in DIALOG_IDS) +
                     rb')_dialog">.*?</dialog>[ \t]*\r?\n', re.S)
    return pat.subn(b"", raw)


def strip_actor_lines(raw):
    pat = re.compile(rb'[ \t]*<actor_dialog>' + PREFIX.encode() + rb'(?:' + b"|".join(d.encode() for d in DIALOG_IDS) +
                     rb')_dialog</actor_dialog>[ \t]*\r?\n')
    return pat.subn(b"", raw)


def strip_script(raw):
    pat = re.compile(rb'^function (?:if_actor_has_materials|transfer_materials)_\w+\(.*?^end[ \t]*\r?\n(?:[ \t]*\r?\n)*', re.S | re.M)
    new, n = pat.subn(b"", raw)
    return new.rstrip(b"\r\n") + b"\r\n", n


def make_text(src, lang):
    raw = open(os.path.join(src, "configs", "text", lang, "st_dialogs_coop_l05_bar.xml"), "rb").read()
    pat = re.compile(rb'[ \t]*<string id="' + PREFIX.encode() + rb'(?:' + b"|".join(d.encode() for d in DIALOG_IDS) +
                     rb')_dialog_\d+">.*?</string>[ \t]*\r?\n', re.S)
    raw, n = pat.subn(b"", raw)
    pat = re.compile(rb'(<string id="' + PREFIX.encode() + rb'start_dialog_0">\s*<text>).*?(</text>)', re.S)
    raw, m = pat.subn(lambda mm: mm.group(1) + GREETING[lang].encode("cp1251") + mm.group(2), raw)
    assert m == 1
    out = os.path.join(TEXT_OUT, lang, "st_dialogs_coop_l05_bar.xml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(raw)
    print("%-60s removed %d strings, greeting replaced" % (os.path.relpath(out, REPO), n))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    edit(DIALOG_XML, strip_dialogs)
    for f in CHAR_FILES:
        edit(f, strip_actor_lines)
    edit(SCRIPT, strip_script)
    for lang in ("eng", "rus"):
        make_text(sys.argv[1], lang)


if __name__ == "__main__":
    main()
