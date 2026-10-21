"""Offline check of the no_tech_parts patch (seconds, no game).

  python offline_check.py [-v] [<mod source gamedata.db0 folder> <mod source gamedata.db1 folder>]

1. both all.spawn files of the repo carry no technician part (and keep contiguous spawn ids, spawn_id field == chunk id);
2. no patch file (xml, ltx, script, lua) refers to the five sections or to the cut dialogs / Lua helpers, except the allowed leftovers below;
3. every `dialogs_item.<fn>` used by a dialog xml of the patches (and of the mod source, when given) exists in the patched dialogs_item.script;
4. every dialog id listed in a character_desc of the patches exists in a dialog xml (patch copy or mod source);
5. the Bar technician and the Army Warehouses technician still have their start dialog, and its string exists in both languages.
Exit code 1 on any failure.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PATCHES = os.path.join(REPO, "patches")
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import strip_spawn as SS  # noqa: E402

FAMILY = SS.FAMILY
PAT_REF = re.compile(r"jup_b200_tech_materials|materials_(?:wire|acetone|textolite|transistor|capacitor)_3x|"
                     r"plyushkin_(?:what_kind_of_junk_is_needed|hand_over_the_trash)")
# (relative path fragment, reason) of leftovers that are allowed
ALLOWED = [
    ("configs/misc/trade/", "bare 'NO TRADE' sell-list lines of the item sections (can_trade = false, nothing is offered)"),
    ("configs/text/", "item name/description strings of the kept sections"),
    ("NOTES.md", "documentation"),
    ("swap_report.txt", "report of an old tool run"),
    ("wip_heli", "work-in-progress copy outside gamedata"),
    ("no_tech_parts/", "this patch (tools, tests, notes)"),
    ("/tools/", "generator scripts"),
]
fails = []


VERBOSE = "-v" in sys.argv
if VERBOSE:
    sys.argv.remove("-v")
passed = 0


def check(name, ok, detail=""):
    global passed
    if ok:
        passed += 1
    else:
        fails.append(name)
    if VERBOSE or not ok:
        print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))


def rel(p):
    return os.path.relpath(p, REPO).replace("\\", "/")


def walk():
    for root, dirs, files in os.walk(PATCHES):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in files:
            yield os.path.join(root, f)


# 1 -------------------------------------------------------------------------------------------------
for p in walk():
    if os.path.basename(p) == "all.spawn" and os.path.getsize(p) > 1000000 and "wip" not in p:
        S = SS.X.AllSpawn(open(p, "rb").read())
        bad = [e.name for e in S.ents if SS.is_part(e)]
        check("all.spawn without parts: " + rel(p), not bad, "%d entities, %d parts" % (len(S.ents), len(bad)))
        ids_ok = all(e.eid == i and SS.spawn_id(e) == i for i, e in enumerate(S.ents))
        check("all.spawn ids contiguous and spawn_id == chunk id: " + rel(p), ids_ok)
        cnt = struct.unpack_from("<I", S.head, 36)[0]
        check("all.spawn header count: " + rel(p), cnt == len(S.ents), "%d vs %d" % (cnt, len(S.ents)))

# 2 -------------------------------------------------------------------------------------------------
left = {}
for p in walk():
    if os.path.splitext(p)[1].lower() not in (".xml", ".ltx", ".script", ".dscript", ".lua", ".py", ".txt", ".md"):
        continue
    r = rel(p)
    try:
        txt = open(p, "rb").read().decode("latin1")
    except OSError:
        continue
    if PAT_REF.search(txt):
        why = next((w for frag, w in ALLOWED if frag in r), None)
        if why:
            left.setdefault(why, []).append(r)
        else:
            check("no reference in " + r, False, PAT_REF.search(txt).group(0))
check("no unexpected reference to the parts / cut dialogs in any patch file", not [f for f in fails if f.startswith("no reference in")])
for why, files in sorted(left.items()):
    print("  left (allowed): %d file(s): %s" % (len(files), why))

# 3 -------------------------------------------------------------------------------------------------
script = os.path.join(PATCHES, "artifact_quests", "gamedata", "scripts", "dialogs_item.script")
defined = set(re.findall(r"^function (\w+)\(", open(script, "rb").read().decode("latin1"), re.M))
xmls = [p for p in walk() if p.endswith(".xml") and "/gameplay/" in p.replace("\\", "/")]
srcs = []
if len(sys.argv) == 3:
    d0 = sys.argv[1]
    for f in os.listdir(os.path.join(d0, "configs", "gameplay")):
        if f.startswith("dialogs_coop_") and f.endswith(".xml") and f.isascii() and " " not in f:   # skips the mod's "copy" backup file
            srcs.append(os.path.join(d0, "configs", "gameplay", f))
    ds = os.path.join(sys.argv[2], "scripts", "dialogs_item.script")
    if os.path.isfile(ds):
        defined_src = set(re.findall(r"^function (\w+)\(", open(ds, "rb").read().decode("latin1"), re.M))
        gone = defined_src - defined
        want = {"%s_materials_%s_3x" % (a, b) for a in ("if_actor_has", "transfer") for b in ("wire", "acetone", "textolite", "transistor", "capacitor")}
        check("patched dialogs_item.script lost exactly the ten parts helpers (other changes of artifact_quests are additions)", gone == want,
              "removed %s" % sorted(gone))
for p in xmls + srcs:
    txt = open(p, "rb").read().decode("latin1")
    for fn in set(re.findall(r"dialogs_item\.(\w+)", txt)):
        if p in srcs and re.search(r"materials_(wire|acetone|textolite|transistor|capacitor)_3x", fn):
            continue   # the mod's own (unpatched) bar dialogs; the patch copy of that file has no such reference (checked in 2)
        check("dialogs_item.%s exists (%s)" % (fn, os.path.basename(p)), fn in defined)

# 4 -------------------------------------------------------------------------------------------------
all_dialogs = set()
for p in xmls + srcs:
    if os.path.basename(p).startswith("dialogs_"):
        all_dialogs |= set(re.findall(r'<dialog id="(\w+)"', open(p, "rb").read().decode("latin1")))
for p in xmls:
    if not os.path.basename(p).startswith("character_desc_coop_l0"):
        continue
    for did in re.findall(r"^[ \t]*<(?:actor_dialog|start_dialog)>(\w+)</", open(p, "rb").read().decode("latin1"), re.M):
        if did.startswith("bar_smart_terrain_10_") or did.startswith("mil_smart_terrain_1"):
            check("dialog %s listed in %s exists" % (did, os.path.basename(p)), did in all_dialogs or not srcs)

# 5 -------------------------------------------------------------------------------------------------
sid = "bar_smart_terrain_10_stalker_plyushkin_start_dialog_0"
for lang in ("eng", "rus"):
    t = open(os.path.join(PATCHES, "no_tech_parts", "gamedata", "configs", "text", lang, "st_dialogs_coop_l05_bar.xml"), "rb").read()
    check("%s greeting string present" % lang, ('<string id="%s">' % sid).encode() in t)
    check("%s cut strings absent" % lang, b"hand_over_the_trash" not in t and b"what_kind_of_junk" not in t)
    check("%s file keeps the other Bar strings" % lang, t.count(b"<string id=") > 100, str(t.count(b"<string id=")))
dx = open(os.path.join(PATCHES, "quest_dialogs", "gamedata", "configs", "gameplay", "dialogs_coop_l05_bar.xml"), "rb").read()
check("start dialog of the technician kept in the Bar dialog xml", b'<dialog id="bar_smart_terrain_10_stalker_plyushkin_start_dialog">' in dx)

print("\n%s: %d failure(s)" % ("FAIL" if fails else "OK", len(fails)))
sys.exit(1 if fails else 0)
