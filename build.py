# Builds zzz_soc_coop_fixes.db from every patches/<fix>/gamedata folder.
# Usage: python build.py [out.db] [--sarcophagus-fps]
# --sarcophagus-fps adds optional/sarcophagus_fps (better FPS in the big Monolith fights, for weaker PCs).
# --skip=a,b leaves those patch folders out (unfinished work). --stage=DIR also keeps the merged gamedata folder in DIR.
import os, shutil, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
extra = ['sarcophagus_fps'] if '--sarcophagus-fps' in sys.argv else []
skip = set(sum([a[7:].split(',') for a in sys.argv[1:] if a.startswith('--skip=')], []))
keep = [a[8:] for a in sys.argv[1:] if a.startswith('--stage=')]
out = os.path.abspath(args[0] if args else os.path.join(here, 'build', 'zzz_soc_coop_fixes.db'))
os.makedirs(os.path.dirname(out), exist_ok=True)
stage = tempfile.mkdtemp(prefix='soc_fixes_')
try:
    for fix in sorted(os.listdir(os.path.join(here, 'patches'))):
        src = os.path.join(here, 'patches', fix, 'gamedata')
        if fix in skip:
            print('skipped', fix)
            continue
        if os.path.isdir(src):
            shutil.copytree(src, stage, dirs_exist_ok=True)
    for fix in extra:
        shutil.copytree(os.path.join(here, 'optional', fix, 'gamedata'), stage, dirs_exist_ok=True)
    if keep:
        shutil.copytree(stage, os.path.join(keep[0], 'gamedata'), dirs_exist_ok=True)
    subprocess.check_call([sys.executable, os.path.join(here, 'tools', 'pack.py'), stage, out])
    print('built', out)
finally:
    shutil.rmtree(stage, ignore_errors=True)
