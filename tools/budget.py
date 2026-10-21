# Size budget of zzz_soc_coop_fixes.db inside coop.addon (one place for build.py, release.py and the tests).
#
# coop.addon is a tar the 32-bit engine reads; with a patch db appended, every byte of the tar must stay below 4 GiB (4294967296).
# Tests on 2026-10-20/21: dbs of 95-98 MB (raw) died at level load with "Cannot map addon file ...level.game / Not enough memory
# resources"; dbs of about 60 MB booted. The installer appends: 512-byte tar header + the db padded to 512 + two zero blocks, padded to a
# 10240-byte record. We keep a MARGIN below 4 GiB on top of that.
#
#   python budget.py <db> [--addon path\to\coop.addon]       exit 0 = fits, 1 = too big
import os, sys

LIMIT = 2 ** 32
MARGIN = 4 * 2 ** 20
BASE_NAMES = ("gamedata.db0", "gamedata.db1", "icon.webp", "metadata.json")
DEFAULT_ADDON = r"C:\X-Ray Multiplayer Extension\game\addons\coop.addon"
# end of the add-on's own tar entries (gamedata.db0, gamedata.db1, icon.webp, metadata.json) in the Shadow of COOP 8.0 coop.addon; used
# when the add-on file is not on this PC
FALLBACK_BASE_END = 4219324416


def tar_base_end(addon):
    """End offset (512-aligned) of the add-on's own entries; entries added by install.ps1 are ignored. None if unreadable."""
    try:
        end, pos = 0, 0
        with open(addon, 'rb') as f:
            while True:
                f.seek(pos)
                h = f.read(512)
                if len(h) < 512 or h[0] == 0:
                    break
                name = h[:100].split(b'\0')[0].decode('ascii', 'replace')
                size = int(h[124:136].strip(b'\0 ') or b'0', 8)
                pos += 512 + ((size + 511) // 512) * 512
                if name in BASE_NAMES:
                    end = pos
        return end or None
    except (OSError, ValueError):
        return None


def installed_size(base_end, db_size):
    """Size of coop.addon after install.ps1 (header, padded data, end blocks, 10240 record padding)."""
    pos = base_end + 512 + ((db_size + 511) // 512) * 512 + 1024
    return ((pos + 10239) // 10240) * 10240


def room(base_end, margin=MARGIN):
    """Largest db size (bytes) that still installs below 4 GiB minus the margin."""
    lo, hi = 0, LIMIT
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if installed_size(base_end, mid) <= LIMIT - margin:
            lo = mid
        else:
            hi = mid - 1
    return lo


def check(db, addon=None, margin=MARGIN):
    """-> (ok, message). Reads the base end from the add-on when it exists, else uses the 8.0 constant."""
    addon = addon or DEFAULT_ADDON
    base_end = tar_base_end(addon) if os.path.exists(addon) else None
    src = 'coop.addon' if base_end else 'built-in coop.addon 8.0 value'
    base_end = base_end or FALLBACK_BASE_END
    size = os.path.getsize(db)
    fin = installed_size(base_end, size)
    free = LIMIT - margin - fin
    msg = ('db %.1f MB, coop.addon would be %.4f GB after install (%s), limit 4 GiB minus %d MB margin: %s %.1f MB'
           % (size / 2 ** 20, fin / 2 ** 30, src, margin // 2 ** 20, 'headroom' if free >= 0 else 'OVER BY', abs(free) / 2 ** 20))
    return free >= 0, msg


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    ad = None
    if '--addon' in args:
        ad = args[args.index('--addon') + 1]
        args = [a for a in args if a not in ('--addon', ad)]
    ok, m = check(args[0], ad)
    print(('BUDGET OK: ' if ok else 'BUDGET FAIL: ') + m)
    sys.exit(0 if ok else 1)
