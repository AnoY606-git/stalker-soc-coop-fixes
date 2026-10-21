# coop_host_cfg.script keeps its Russian comment texts as Lua decimal escapes of UTF-8 (\208\159 ...), so the file stays ASCII
# (tools\luabal.py reads scripts as cp1251) and coop_settings.ltx is still written as UTF-8.
#   python ru_escape.py --decode > readable.txt     the script with readable Russian (UTF-8), to edit or review
#   python ru_escape.py --encode readable.txt       writes the escaped script back over coop_host_cfg.script
import os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, '..', 'gamedata', 'scripts', 'coop_host_cfg.script')
ESC = re.compile(r'(?:\\[12]\d\d)+')


def dec(m):
    return bytes(int(x) for x in re.findall(r'\\(\d{3})', m.group(0))).decode('utf-8')


if '--decode' in sys.argv:
    s = open(script, 'rb').read().decode('ascii')
    sys.stdout.reconfigure(encoding='utf-8')
    print(ESC.sub(dec, s), end='')
elif '--encode' in sys.argv:
    src = open(sys.argv[sys.argv.index('--encode') + 1], 'rb').read().decode('utf-8')
    out = ''.join(c if ord(c) < 128 else ''.join('\\%03d' % b for b in c.encode('utf-8')) for c in src)
    open(script, 'wb').write(out.encode('ascii'))
else:
    sys.exit(__doc__)
