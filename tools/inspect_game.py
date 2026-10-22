"""Look inside the installed game without unpacking it: base xrMPE archives (game\\resources, game\\patches) and every
archive inside coop.addon (the mod's gamedata.db*, and zzz_soc_coop_fixes.db when the fix patch is installed).

usage (python 3, from the repo root; set XRMPE_GAME if the game is not in C:\\X-Ray Multiplayer Extension\\game):
  python -I tools\\inspect_game.py grep "<regex>" [--ext .script,.ltx,.xml]   every matching line, with archive and file
  python -I tools\\inspect_game.py sections <section> [...]                  where each config section is defined (last one wins) + its RU name
  python -I tools\\inspect_game.py extract <outdir> <path\\in\\archive> [...]  every archive's copy of a file, as <archive>__<file>
  python -I tools\\inspect_game.py models <stage gamedata>                   every .ogf of a build stage: its models\\capture file and the damage
                                                                            sections it names must exist (missing ones crash the game when an
                                                                            NPC with that model appears: "Can't open section ...")
  python -I tools\\inspect_game.py save <file.scop | folder>                 unpack co-op saves, size, player names found, a search for text

Examples from real fixes: `grep "kombez_antigas"` found the Duty models of a Garbage crash; `sections wpn_pb killer_outfit` showed that
killer_outfit does not exist in this mod before it went into a trader list; `grep "mp_device_torch"` found the scene effects that need the
multiplayer flashlight.
"""
import glob
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "stalker_xrmpe"))
import xdb  # noqa: E402

GAME = os.environ.get("XRMPE_GAME", r"C:\X-Ray Multiplayer Extension\game")
ADDON = os.path.join(GAME, "addons", "coop.addon")


def sources(with_fixes=True):
    """(path, label, offset, size) of every archive, in load order: base first, then the addon members."""
    out = []
    for r in ("resources", "patches"):
        for q in sorted(glob.glob(os.path.join(GAME, r, "*"))):
            if os.path.isfile(q):
                out.append((q, os.path.basename(q), 0, os.path.getsize(q)))
    if os.path.isfile(ADDON):
        for m, (o, s) in xdb.tar_members(ADDON).items():
            if with_fixes or "zzz_soc" not in m:
                out.append((ADDON, m, o, s))
    return out


def walk(pred, with_fixes=True):
    """yield (label, name, text bytes) for every archive entry whose lower-case name passes pred"""
    for path, label, off, size in sources(with_fixes):
        f = open(path, "rb")
        try:
            ents = xdb.index(f, off, size)
        except Exception:
            continue
        for name, rs, cs, ptr in ents:
            if rs and pred(name.lower()):
                f.seek(off + ptr)
                d = f.read(cs)
                if rs != cs:
                    d = xdb.lzo1x(d, rs)
                yield label, name, d


def cmd_grep(args):
    pat = re.compile(args[0])
    exts = (".script", ".dscript", ".ltx", ".xml")
    if "--ext" in args:
        exts = tuple(args[args.index("--ext") + 1].split(","))
    for label, name, d in walk(lambda n: n.endswith(exts)):
        for i, line in enumerate(d.decode("cp1251", "replace").splitlines()):
            if pat.search(line):
                print("%s:%s:%d: %s" % (label, name, i + 1, line.strip()[:200]))


def cmd_sections(args):
    want = {w: [] for w in args}
    names = {}
    for label, name, d in walk(lambda n: n.endswith(".ltx") or (n.endswith(".xml") and "text\\rus" in n)):
        t = d.decode("cp1251", "replace")
        if name.lower().endswith(".ltx"):
            for m in re.finditer(r"(?m)^\[([^\]]+)\]", t):
                if m.group(1) in want:
                    want[m.group(1)].append(label + ":" + name)
        else:
            for w in want:
                m = re.search(r'id="%s_name"\s*>\s*<text>([^<]*)' % re.escape(w), t)
                if m:
                    names[w] = m.group(1)
    for w, where in want.items():
        print(w.ljust(28), names.get(w, ""), "|", where[-1] if where else "MISSING")


def cmd_extract(args):
    out, wanted = args[0], set(a.lower() for a in args[1:])
    os.makedirs(out, exist_ok=True)
    for label, name, d in walk(lambda n: n in wanted):
        dst = os.path.join(out, label.replace(".", "_") + "__" + name.split("\\")[-1])
        open(dst, "wb").write(d)
        print(dst, len(d))


def cmd_models(args):
    stage = args[0]
    files = {}
    for label, name, d in walk(lambda n: n.startswith("configs\\") and n.endswith(".ltx"), with_fixes=False):
        files[name.lower()] = d.decode("cp1251", "replace")
    for p in glob.glob(os.path.join(stage, "configs", "**", "*.ltx"), recursive=True):
        files[os.path.relpath(p, stage).lower()] = open(p, "rb").read().decode("cp1251", "replace")
    sections = set()
    for t in files.values():
        sections.update(m.group(1).lower() for m in re.finditer(r"(?m)^\[([^\]]+)\]", t))
    bad = 0
    ogfs = glob.glob(os.path.join(stage, "meshes", "**", "*.ogf"), recursive=True)
    for o in ogfs:
        b = open(o, "rb").read()
        for ref in sorted(set(m.decode().lower() for m in re.findall(rb"models\\capture\\[A-Za-z0-9_]+", b))):
            key = "configs\\" + ref + ".ltx"
            if key not in files:
                print("MISSING FILE", os.path.relpath(o, stage), ref)
                bad += 1
                continue
            for k in ("bones_protection_sect", "immunities_sect"):
                m = re.search(r"(?m)^\s*%s\s*=\s*([\w.]+)" % k, files[key])
                if m and m.group(1).lower() not in sections:
                    print("MISSING SECTION", os.path.relpath(o, stage), ref, k, "=", m.group(1))
                    bad += 1
    print(len(ogfs), "ogf checked,", bad, "problems (player outfit meshes with gilet_mask_damage / kombez_kupol_damage are known and harmless)")


def cmd_save(args):
    paths = sorted(glob.glob(os.path.join(args[0], "*.scop"))) if os.path.isdir(args[0]) else [args[0]]
    find = args[1].encode("cp1251") if len(args) > 1 else None
    for p in paths:
        b = open(p, "rb").read()
        size = struct.unpack_from("<I", b, 8)[0]
        try:
            d = xdb.lzo1x(b[12:], size)
        except Exception as e:
            print(os.path.basename(p), "cannot unpack:", e)
            continue
        extra = ""
        if find:
            extra = " | '%s' found %d times" % (args[1], d.count(find))
        print("%s: %d bytes unpacked%s" % (os.path.basename(p), len(d), extra))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3 or sys.argv[1] not in ("grep", "sections", "extract", "models", "save"):
        print(__doc__)
        return 2
    globals()["cmd_" + sys.argv[1]](sys.argv[2:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
