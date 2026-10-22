"""Build a TEST-ONLY copy of coop.addon with extra Lua appended to shipped scripts.  (python -I qa_build.py ...)

  python -I qa_build.py --out qa_mylane.addon --append scripts/xr_conditions.dscript=lua/qa_harness.lua,my_hooks.lua
                        [--append scripts/_g.script=...]   (repeatable)
                        [--extra-dir DIR]                   (DIR maps to gamedata\\; copied into the test db as-is)
                        [--game "C:\\X-Ray Multiplayer Extension\\game"] [--base coop.addon] [--min-free-gb 6]

For every --append the EFFECTIVE shipped version of the script (last db in the base addon that has it, e.g. the Shadow of COOP
patch db) is read straight out of the base addon, the Lua files are appended, and the result goes into a test db
`zzzz_qa_<name>.db` (packed with pack.py) that is appended to a COPY of the base addon with tarfile mode 'a'.
The base addon is never modified.  The copy is ~4.2 GB: the build refuses to run if free disk space after the copy would be
below --min-free-gb.  The caller deletes the copy afterwards (run_coop.ps1 does).  Prints BUILD_OK <path> or BUILD_FAIL <why>.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xdb  # noqa: E402


def effective_file(addon_path, rel, extra_dbs=()):
    """Return bytes of `rel` (like scripts/xr_conditions.dscript) from the last db of the addon that contains it."""
    want = rel.replace("/", "\\").lower()
    members = xdb.tar_members(addon_path)
    found = None
    with open(addon_path, "rb") as f:
        for name in sorted(members):
            if not name.lower().endswith((".db", ".db0", ".db1", ".db2", ".db3", ".db4", ".db5")):
                continue
            off, size = members[name]
            for ename, rs, cs, ptr in xdb.index(f, off, size):
                if ename.lower() == want and rs:
                    found = (name, off, rs, cs, ptr)
    for dbp in extra_dbs:          # --db-file dbs are appended after the base members: they win over the base addon
        with open(dbp, "rb") as g:
            for ename, rs, cs, ptr in xdb.index(g, 0, os.path.getsize(dbp)):
                if ename.lower() == want and rs:
                    g.seek(ptr)
                    data = g.read(cs)
                    if rs != cs:
                        data = xdb.lzo1x(data, rs)
                    found = (os.path.basename(dbp), data)
    if not found:
        return None, None
    if len(found) == 2:
        return found[1], found[0]
    with open(addon_path, "rb") as f:
        name, off, rs, cs, ptr = found
        f.seek(off + ptr)
        data = f.read(cs)
        if rs != cs:
            data = xdb.lzo1x(data, rs)
        return data, name


LUAVENV = os.environ.get("QA_LUA_PY", sys.executable)   # a python with lupa installed (pip install lupa)
LUACHECK = ("import sys,lupa.lua51 as l\nlua=l.LuaRuntime()\nf=lua.eval('function(s) local f,e=loadstring(s) return e end')\n"
            "e=f(open(sys.argv[1],'rb').read())\nprint('LUAERR '+str(e) if e else 'LUAOK')\n")


def lua_syntax(path):
    """Parse with real Lua 5.1 (lupa) when available. Returns None if ok / not checkable, else the error text."""
    for py in (sys.executable, LUAVENV):
        if py and os.path.exists(py):
            r = subprocess.run([py, "-c", LUACHECK, path], capture_output=True, text=True)
            if "LUAOK" in r.stdout:
                return None
            if "LUAERR" in r.stdout:
                return r.stdout.strip()
    return None


QA_LIB = os.path.join(HERE, "lua", "qa_lib.lua")


def expand_qa_lib(files):
    """Opt-in: a hooks file whose first 30 lines contain `--@qa_lib` gets lua/qa_lib.lua appended right before it
    (once, and only if qa_lib.lua is not already in the list).  Files without the marker are untouched."""
    if any(os.path.abspath(f).lower() == QA_LIB.lower() for f in files):
        return files
    out = []
    added = False
    for f in files:
        if not added and os.path.abspath(f).lower() != os.path.join(HERE, "lua", "qa_harness.lua").lower() and os.path.exists(f):
            with open(f, "rb") as fh:
                head = b"\n".join(fh.read(4096).splitlines()[:30])
            if b"--@qa_lib" in head:
                out.append(QA_LIB)
                added = True
        out.append(f)
    return out


def inplace_patch(addon, dirs):
    """Overwrite uncompressed entries of the db members of the (copied) addon with the files of dirs (same relative path)."""
    members = xdb.tar_members(addon)
    want = {}
    for d in dirs:
        for root, _, files in os.walk(d):
            for fn in files:
                full = os.path.join(root, fn)
                want[os.path.relpath(full, d).lower().replace("/", "\\")] = full
    done = set()
    with open(addon, "r+b") as f:
        for name, (off, size) in sorted(members.items()):
            if not name.lower().endswith((".db", ".db0", ".db1", ".db2", ".db3", ".db4", ".db5")):
                continue
            for ename, rs, cs, ptr in xdb.index(f, off, size):
                key = ename.lower()
                if key in want and rs:
                    new = open(want[key], "rb").read()
                    if rs != cs or len(new) > rs:
                        print("inplace SKIPPED %s in %s: stored %d/%d, new %d bytes (compressed or larger)" % (ename, name, rs, cs, len(new)))
                        continue
                    f.seek(off + ptr)
                    f.write(new + bytes(rs - len(new)))
                    done.add(key)
                    print("inplace %s in %s (%d of %d bytes)" % (ename, name, len(new), rs))
    missing = sorted(set(want) - done)
    if missing:
        print("inplace: not in the base addon (skipped): %s" % ", ".join(missing))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="test addon file name (placed in <game>\\addons)")
    ap.add_argument("--owner", required=True, help="your slot owner name: you must hold the game slot (stalker_slot.py acquire) to build")
    ap.add_argument("--delete", help="delete this test addon (shipped addons are refused) instead of building")
    ap.add_argument("--append", action="append", default=[], help="scripts/<file>=<lua>[,<lua>...]")
    ap.add_argument("--extra-dir", action="append", default=[])
    ap.add_argument("--db-file", action="append", default=[],
                    help="a finished .db (e.g. the compressed release zzz_soc_coop_fixes.db) appended to the test addon as zzz_soc_coop_fixes_rel.db, "
                         "byte for byte like install.ps1 appends it (tar mtime 0, uid 0), BEFORE the test db. The faithful way to boot-check a release.")
    ap.add_argument("--inplace-dir", action="append", default=[],
                    help="DIR maps to gamedata\; files that already exist UNCOMPRESSED in the base addon dbs and are not larger are overwritten in "
                         "the COPY in place (zero padded). For big replacements: the addon file must stay below 4 GB (32-bit offsets), see NOTES of soc_levels")
    ap.add_argument("--game", default=r"C:\X-Ray Multiplayer Extension\game")
    ap.add_argument("--base", default="coop.addon")
    ap.add_argument("--min-free-gb", type=float, default=6.0)
    ap.add_argument("--keep-stage", default="")
    ap.add_argument("--db-to", default="", help="write only the test db into this folder (no addon copy)")
    ap.add_argument("--lane", default="", help="reuse the permanent copy addons\\qalane<N>.addon: cut it back to the base addon's data and append the test db")
    a = ap.parse_args()

    addons = os.path.join(a.game, "addons")
    sys.path.insert(0, HERE)
    os.environ["STALKER_GAME_DIR"] = a.game
    import stalker_slot  # noqa: E402
    if a.delete:
        t = os.path.join(addons, a.delete)
        if a.delete.lower() in stalker_slot.SHIPPED_ADDONS or not a.delete.lower().endswith(".addon"):
            print("BUILD_FAIL refusing to delete " + a.delete)
            return 1
        if os.path.exists(t):
            os.remove(t)
        print("DELETED " + a.delete)
        return 0
    if not a.out:
        print("BUILD_FAIL --out required")
        return 1
    # HARD RULE: a test addon copy (4.2 GB) may only be created while holding the game slot, and only one may exist PC-wide.
    # (--db-to / --lane make no new copy: the guard does not apply; the lane is tied to the caller's slot index)
    if not a.db_to and not a.lane and stalker_slot.main(["guard", "--owner", a.owner]) != 0:
        print("BUILD_FAIL guard denied (hold the slot first, and no other test addon may exist)")
        return 1
    base = os.path.join(addons, a.base)
    out = os.path.join(addons, a.out)
    if os.path.abspath(out).lower() == base.lower():
        print("BUILD_FAIL refusing to overwrite the base addon")
        return 1
    lane_ok = False
    if a.lane:
        out = os.path.join(addons, "qalane%s.addon" % a.lane)
        meta_p = out + ".json"
        st = os.stat(base)
        try:
            meta = json.load(open(meta_p))
            lane_ok = (os.path.exists(out) and meta.get("base_size") == st.st_size and meta.get("base_mtime") == int(st.st_mtime)
                       and os.path.getsize(out) >= meta["base_end"])
        except (OSError, ValueError, KeyError):
            lane_ok = False
    elif os.path.exists(out):
        print("BUILD_FAIL output exists: " + out)
        return 1
    need = 0 if (a.db_to or lane_ok) else os.path.getsize(base)
    free = shutil.disk_usage(addons).free
    if (free - need) / 2**30 < a.min_free_gb:
        print("BUILD_FAIL low disk: %.1f GB free, copy needs %.1f GB, keep >= %.1f GB" % (free / 2**30, need / 2**30, a.min_free_gb))
        return 1

    stage = tempfile.mkdtemp(prefix="qa_stage_")
    try:
        for spec in a.append:
            rel, files = spec.split("=", 1)
            data, src = effective_file(base, rel, a.db_file)
            if data is None:
                print("BUILD_FAIL %s not found in %s" % (rel, a.base))
                return 1
            buf = bytearray(data)
            if not buf.endswith(b"\n"):
                buf += b"\n"
            for lf in expand_qa_lib(files.split(",")):
                with open(lf, "rb") as fh:
                    buf += b"\n-- ==== appended test file: " + os.path.basename(lf).encode() + b" ====\n" + fh.read() + b"\n"
            dst = os.path.join(stage, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(buf)
            err = lua_syntax(dst)
            if err:
                print("BUILD_FAIL lua syntax in patched %s: %s" % (rel, err))
                return 1
            print("patched %s (from %s) + %s" % (rel, src, files))
        for d in a.extra_dir:
            shutil.copytree(d, stage, dirs_exist_ok=True)
        dbname = "zzzz_qa_" + os.path.splitext(a.out)[0] + ".db"
        dbpath = os.path.join(tempfile.gettempdir(), dbname)
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "pack.py"), stage, dbpath], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            print("BUILD_FAIL pack: " + r.stderr[-300:])
            return 1
        if a.db_to:
            # fast mode: the db goes into a per-run patches folder (run_coop -FastPatch), the base addon is used as is
            os.makedirs(a.db_to, exist_ok=True)
            dst = os.path.join(a.db_to, dbname)
            shutil.move(dbpath, dst)
            print("BUILD_OK " + dst)
            return 0
        if a.lane:
            meta_p = out + ".json"
            if a.inplace_dir or (os.path.exists(meta_p) and json.load(open(meta_p)).get("dirty")):
                lane_ok = False   # in-place edits change the base part: re-copy before and after such a run
            if not lane_ok:
                print("lane %s: making the permanent copy (once per coop.addon version)" % a.lane)
                shutil.copyfile(base, out)
                end = max(off + ((size + 511) // 512) * 512 for nm, (off, size) in xdb.tar_members(base).items() if nm != "zzz_soc_coop_fixes.db")   # an installed fix db is not part of the base (a 55 MB release db there would push base + test db past 4 GiB)
                st = os.stat(base)
                json.dump({"base_size": st.st_size, "base_mtime": int(st.st_mtime), "base_end": end,
                           "dirty": bool(a.inplace_dir)}, open(meta_p, "w"))
            meta = json.load(open(meta_p))
            with open(out, "r+b") as fh:          # drop the previous test db (and the tar end blocks)
                fh.truncate(meta["base_end"])
                fh.seek(0, 2)
                fh.write(b"\0" * 1024)             # tar end-of-archive, so mode 'a' appends right after the base members
        else:
            shutil.copyfile(base, out)
        if a.inplace_dir:
            try:
                inplace_patch(out, a.inplace_dir)
            except Exception as e:  # noqa: BLE001
                os.remove(out)
                print("BUILD_FAIL inplace: %r" % e)
                return 1
        try:
            with tarfile.open(out, "a", format=tarfile.USTAR_FORMAT) as tf:
                for dbf in a.db_file:
                    ti = tf.gettarinfo(dbf, arcname="zzz_soc_coop_fixes_rel.db")
                    ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = 0, 0, 0, "", "", 0o644
                    with open(dbf, "rb") as fh:
                        tf.addfile(ti, fh)
                tf.add(dbpath, arcname=dbname)
        except Exception as e:  # noqa: BLE001
            os.remove(out)
            print("BUILD_FAIL tar: %r" % e)
            return 1
        finally:
            os.remove(dbpath)
        members = xdb.tar_members(out)
        if dbname not in members:
            os.remove(out)
            print("BUILD_FAIL test db missing from the copy")
            return 1
        print("BUILD_OK " + out)
        return 0
    finally:
        if a.keep_stage:
            shutil.copytree(stage, a.keep_stage, dirs_exist_ok=True)
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
