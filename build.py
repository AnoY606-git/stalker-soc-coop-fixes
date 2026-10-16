# Builds zzz_soc_coop_fixes.db from every patches/<fix>/gamedata folder.
# Usage: python build.py [out.db] [--corpse-cap-30]
# --corpse-cap-30 adds optional/corpse_cap_30 (fewer corpses kept, better FPS in big fights).
import os, shutil, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
extra = ['corpse_cap_30'] if '--corpse-cap-30' in sys.argv else []
out = os.path.abspath(args[0] if args else os.path.join(here, 'build', 'zzz_soc_coop_fixes.db'))
os.makedirs(os.path.dirname(out), exist_ok=True)
stage = tempfile.mkdtemp(prefix='soc_fixes_')
try:
    for fix in sorted(os.listdir(os.path.join(here, 'patches'))):
        src = os.path.join(here, 'patches', fix, 'gamedata')
        if os.path.isdir(src):
            shutil.copytree(src, stage, dirs_exist_ok=True)
    for fix in extra:
        shutil.copytree(os.path.join(here, 'optional', fix, 'gamedata'), stage, dirs_exist_ok=True)
    subprocess.check_call([sys.executable, os.path.join(here, 'tools', 'pack.py'), stage, out])
    print('built', out)
finally:
    shutil.rmtree(stage, ignore_errors=True)
