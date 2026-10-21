"""Extracts the SoC Duty checkpoint assets of the garbage_duty patch (offline, read only).

  python extract_assets.py [<out gamedata dir>]

Meshes and textures: the SoC models as they are in the CoP port add-on `shadow_of_chernobyl.addon` (the version that already runs on xrMPE;
the Steam .ogf files differ by 756 bytes each). Voices: the English SoC recordings of the Steam install (tools\\xdb_soc.py), the Russian ones
are already in the mod (`characters_voice\\scenario\\coop_l02_garbage\\duty_after_rush_*.ogg`, same files as SoC).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import xdb  # noqa: E402

ADDON = os.path.expanduser(r"~\Downloads\soc_ai_port\extracted\shadow_of_chernobyl.addon")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "gamedata")
WANT = [
    r"meshes\actors\dolg\stalker_do_balon_4.ogf",
    r"meshes\actors\dolg\stalker_do_balon_8.ogf",
    r"meshes\actors\dolg\stalker_do_balon_80.ogf",
    r"meshes\actors\dolg\stalker_do_antigas.ogf",
    r"textures\act\act_soldier_head1.dds",
]


def main():
    members = xdb.tar_members(ADDON)
    found = {}
    with open(ADDON, "rb") as f:
        for name, (off, size) in members.items():
            if ".db" not in name:
                continue
            for ename, rs, cs, ptr in xdb.index(f, off, size):
                if ename.lower() in WANT:
                    f.seek(off + ptr)
                    d = f.read(cs)
                    if rs != cs:
                        d = xdb.lzo1x(d, rs)
                    found[ename.lower()] = d
    for w in WANT:
        d = found.get(w)
        if d is None:
            print("MISSING in port add-on:", w)
            continue
        p = os.path.join(OUT, w)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(d)
        print("wrote", w, len(d))
    # English voices from the Steam SoC archives
    tmp = os.path.join(HERE, "_steam_tmp")
    os.makedirs(tmp, exist_ok=True)
    subprocess.check_call([sys.executable, "-I", os.path.join(REPO, "tools", "xdb_soc.py"),
                           r"characters_voice.scenario.garbage.duty_after_rush_(bad|good)", "x", tmp], cwd=tmp)
    for n in ("bad", "good"):
        src = os.path.join(tmp, "sounds", "characters_voice", "scenario", "garbage", "duty_after_rush_%s.ogg" % n)
        dst = os.path.join(OUT, "sounds", "characters_voice", "scenario", "coop_l02_garbage", "eng", "duty_after_rush_%s.ogg" % n)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(open(src, "rb").read())
        print("wrote", dst)


if __name__ == "__main__":
    main()
