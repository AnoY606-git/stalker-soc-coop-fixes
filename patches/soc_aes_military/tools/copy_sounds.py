"""Copies the SoC radio lines named in the RADIO table of coop_soc_aes_military.script into the patch, in both languages.

  python copy_sounds.py <steam soc extract dir> [<Russian SoC add-on file>]

<steam soc extract dir> = xdb_soc.py extraction of the Steam SoC (English recordings, it has sounds\\characters_voice\\scenario\\aes\\...), made with
    python -I tools\\xdb_soc.py "characters_voice.scenario.aes" x <dir>
<Russian SoC add-on file> = shadow_of_chernobyl.addon of the CoP port (the Russian recordings; default ~\\Downloads\\soc_ai_port\\extracted\\shadow_of_chernobyl.addon).
The Steam and the Russian files are DIFFERENT recordings (the same names, other bytes), so each language gets its own copy.
Files are copied byte for byte (original SoC ogg files with their comment header) to
  gamedata\\sounds\\characters_voice\\scenario\\aes\\eng\\<line>.ogg   (aes2\\ sub folder for the second half of the scenario)
  gamedata\\sounds\\characters_voice\\scenario\\aes\\rus\\<line>.ogg
Idempotent. Files of the patch that the table no longer names are removed. Prints the total size (patch limit 3 MB for everything).
"""
import os
import re
import shutil
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.dirname(here)
repo = os.path.dirname(os.path.dirname(patch))
sys.path.insert(0, os.path.join(repo, 'tools'))

src = sys.argv[1]
addon = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser(r'~\Downloads\soc_ai_port\extracted\shadow_of_chernobyl.addon')
script = open(os.path.join(patch, 'gamedata', 'scripts', 'coop_soc_aes_military.script'), encoding='utf-8').read()
block = script[script.index('RADIO = {'):script.index('local RADIO_DIR')]
lines = re.findall(r'"([A-Za-z0-9_\\]+)"', block)
lines = [l for l in lines if l.startswith('aes')]
names = []
for l in lines:
    n = l.replace('\\\\', '/').replace('\\', '/')
    if n not in names:
        names.append(n)

# Russian recordings out of the add-on
import xdb  # noqa: E402

wanted = {('sounds\\characters_voice\\scenario\\aes\\' + n.replace('/', '\\') + '.ogg').lower(): n for n in names}
rus = {}
with open(addon, 'rb') as f:
    for member, (off, size) in xdb.tar_members(addon).items():
        if '.db' not in member:
            continue
        for ename, rs, cs, ptr in xdb.index(f, off, size):
            n = wanted.get(ename.lower())
            if n is not None:
                f.seek(off + ptr)
                d = f.read(cs)
                if rs != cs:
                    d = xdb.lzo1x(d, rs)
                rus[n] = d

root_src = os.path.join(src, 'sounds', 'characters_voice', 'scenario', 'aes')
root_dst = os.path.join(patch, 'gamedata', 'sounds', 'characters_voice', 'scenario', 'aes')
total = 0
want = set()
for n in names:
    a = os.path.join(root_src, *n.split('/')) + '.ogg'
    if not os.path.isfile(a):
        sys.exit('missing in the Steam SoC extraction: ' + a)
    if n not in rus:
        sys.exit('missing in the Russian SoC add-on: ' + n)
    for lang in ('eng', 'rus'):
        b = os.path.join(root_dst, lang, *n.split('/')) + '.ogg'
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if lang == 'eng':
            shutil.copyfile(a, b)
        else:
            open(b, 'wb').write(rus[n])
        want.add(os.path.normpath(b))
        total += os.path.getsize(b)
for dp, dn, fn in os.walk(root_dst):
    for f in fn:
        p = os.path.normpath(os.path.join(dp, f))
        if p not in want:
            os.remove(p)
            print('removed', p)
for dp, dn, fn in os.walk(root_dst, topdown=False):
    if not os.listdir(dp):
        os.rmdir(dp)
print('%d lines x 2 languages = %d files, %.2f MB' % (len(names), len(want), total / 1e6))
