"""Static check of patch soc_aes_war (fighting helicopters + army BTR on CNPP-1). Offline, seconds. Needs numpy (xrspawn of patch soc_levels).

  python check_war_chain.py <mod source dir (has gamedata.db0)> [--spawn <all.spawn>] [--soc-level-spawn <SoC l12_stancia level.spawn>] [--base-cfg <dir with the xrMPE base configs>]
                            [--addon-names <text file with the file names of the add-on, one per line>]

Proves (exit code 1 on any problem):
  1. the 8 helicopters of the mod (aes_1_heli_attack_1..8) are in all.spawn and their custom data points to scripts\\coop_l11_stancia_1\\aes_1_heli_attack_<n>.ltx,
     the files exist in this patch; every path_move of every file is a patrol path of all.spawn (an abort of the engine otherwise); every section named by
     on_info / on_timer exists in the same file; the four old section names (idle, fly_ready, fly_0, fly_1) are kept (old saves); no file names a rocket
  2. the BTR: the route exists in all.spawn with enough points, its point 9 has a level vertex and a game vertex; the spawn section carries every key of
     [m_car] (script class, binding), the visual / the logic file / the story id; the visual is a file of the add-on and the model config exists in the base
     configs; the logic file names an existing route; no other patch ships the spawn section file, the heli files or the switch file
  3. the SoC helicopter zones of the script equal the SoC restrictors aes_actor_heli, _heli1, _heli2, _heli3 (position + boxes)
  4. the story flags SOC_AESW_DOWN_1..3 the radio of soc_aes_military waits for are given by this script
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PATCH))
sys.path.insert(0, os.path.join(REPO, 'patches', 'soc_levels', 'tools'))
sys.path.insert(0, os.path.join(REPO, 'patches', 'soc_aes_military', 'tools'))
import xrspawn as X  # noqa: E402

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
mod = args[0]


def opt(name, default=None):
    if name in args:
        return args[args.index(name) + 1]
    return default


SPAWN = opt('--spawn', os.path.join(REPO, 'patches', 'darkvalley_restore', 'gamedata', 'spawns', 'all.spawn'))
SOC = opt('--soc-level-spawn')
BASE = opt('--base-cfg')
NAMES = opt('--addon-names')
problems = 0


def ok(msg):
    print('ok      ' + msg)


def bad(msg):
    global problems
    problems += 1
    print('PROBLEM ' + msg)


raw = open(SPAWN, 'rb').read()
S = X.AllSpawn(raw)
P = X.Patrols(dict(X.chunks(raw))[3])
paths = {p['name']: p for p in P.paths}
ents = {e.name: e for e in S.ents}
cfgdir = os.path.join(PATCH, 'gamedata', 'configs', 'scripts', 'coop_l11_stancia_1')
script = open(os.path.join(PATCH, 'gamedata', 'scripts', 'coop_soc_aes_war.script'), 'rb').read().decode('utf-8').replace('\r\n', '\n')

# ---- 1. helicopters
for n in range(1, 9):
    name = 'aes_1_heli_attack_%d' % n
    e = ents.get(name)
    if e is None or e.section != 'helicopter':
        bad('%s is not a helicopter of all.spawn' % name)
        continue
    cd = e.custom().replace('\r\n', '\n')
    want = 'scripts\\coop_l11_stancia_1\\%s.ltx' % name
    if want not in cd:
        bad('%s custom data does not point to %s: %r' % (name, want, cd))
    f = os.path.join(cfgdir, name + '.ltx')
    if not os.path.isfile(f):
        bad('missing ' + f)
        continue
    text = open(f, 'rb').read().decode('ascii').replace('\r\n', '\n')
    secs = re.findall(r'^\[([^\]]+)\]', text, re.M)
    for old in ('heli_move@idle', 'heli_move@fly_ready', 'heli_move@fly_0', 'heli_move@fly_1'):
        if old not in secs:
            bad('%s lost the old section %s (saves)' % (name, old))
    for m in re.finditer(r'^path_move\s*=\s*(\S+)', text, re.M):
        if m.group(1) not in paths:
            bad('%s: path_move %s is not a patrol path of all.spawn' % (name, m.group(1)))
    for m in re.finditer(r'^(?:on_info|on_timer)\s*=\s*(.*)$', text, re.M):
        for alt in m.group(1).split(','):
            target = re.sub(r'^\s*(\{[^}]*\})?\s*(\d+\s*\|)?\s*', '', alt).split()[0]
            if target not in secs:
                bad('%s: switch to the unknown section %s' % (name, target))
    if re.search(r'^use_rocket\s*=\s*true', text, re.M):
        bad('%s allows rockets' % name)
    if not re.search(r'^\[logic\]\nactive = heli_move@idle', text, re.M):
        bad('%s: [logic] active is not heli_move@idle' % name)
ok('8 helicopters: all.spawn entries, files, paths, sections, old section names, no rockets')

# ---- 2. BTR
route = re.search(r'PATH\s*=\s*"([^"]+)"', script).group(1)
idx = int(re.search(r'IDX\s*=\s*(\d+)', script).group(1))
if route not in paths:
    bad('BTR route %s is not a patrol path' % route)
else:
    pts = paths[route]['points']
    if len(pts) <= idx:
        bad('BTR route has %d points, the script wants point %d' % (len(pts), idx))
    else:
        q = pts[idx]
        ok('BTR route %s: %d points, start %d at (%.1f, %.1f, %.1f) lvid %d gvid %d, end at (%.1f, %.1f, %.1f)' % (
            route, len(pts), idx, q['pos'][0], q['pos'][1], q['pos'][2], q['lvid'], q['gvid'], pts[-1]['pos'][0], pts[-1]['pos'][1], pts[-1]['pos'][2]))
        if q['lvid'] >= 4000000000 or q['gvid'] >= 65000:
            bad('BTR start point has no valid vertex ids')
        if 'sig=final' not in pts[-1]['name']:
            ok('(the route end has no signal; the BTR simply stops there)')
sec = open(os.path.join(PATCH, 'gamedata', 'configs', 'creatures', 'spawn_sections_coop_l11_control_monolith.ltx'), 'rb').read().decode('ascii').replace('\r\n', '\n')
orig = open(os.path.join(mod, 'gamedata.db0', 'configs', 'creatures', 'spawn_sections_coop_l11_control_monolith.ltx'), 'rb').read().decode('ascii').replace('\r\n', '\n')
(ok if sec.startswith(orig.rstrip('\n')) else bad)('spawn_sections_coop_l11_control_monolith.ltx starts with the mod file byte for byte')
body = sec[sec.index('[soc_aes_btr]'):]
keys = dict((m.group(1), m.group(2).strip()) for m in re.finditer(r'^(\S+)\s*=\s*(.*)$', body, re.M))
msys = None
for cand in (os.path.join(BASE or '', 'system.ltx'), os.path.join(mod, 'gamedata.db0', 'configs', 'system.ltx')):
    if os.path.isfile(cand):
        t = open(cand, 'rb').read().decode('cp1251', 'replace')
        if '[m_car]' in t:
            msys = t
            break
if msys is None:
    bad('no system.ltx with [m_car] found')
else:
    mcar = msys[msys.index('[m_car]'):]
    mcar = mcar[:mcar.index('\n[', 5)] if '\n[' in mcar[5:] else mcar
    mk = dict((m.group(1), m.group(2).strip()) for m in re.finditer(r'^(\S+)\s*=\s*(.*)$', mcar, re.M))
    for k, v in mk.items():
        if keys.get(k, '').replace(' ', '') != v.replace(' ', ''):
            bad('[soc_aes_btr] differs from [m_car] in %s: %r vs %r' % (k, keys.get(k), v))
    ok('[soc_aes_btr] repeats every key of [m_car] (class %s, binding %s)' % (keys.get('class'), keys.get('script_binding')))
vis = keys.get('visual', '')
logic_file = keys.get('custom_data', '')
(ok if vis else bad)('visual ' + vis)
(ok if os.path.isfile(os.path.join(PATCH, 'gamedata', 'configs', logic_file)) else bad)('logic file ' + logic_file)
lf = open(os.path.join(PATCH, 'gamedata', 'configs', logic_file), 'rb').read().decode('ascii')
wp = re.search(r'^path_walk\s*=\s*(\S+)', lf, re.M).group(1)
(ok if wp == route else bad)('the logic file drives the route the script creates the BTR on (%s)' % wp)
(ok if keys.get('story_id') == re.search(r'STORY\s*=\s*"([^"]+)"', script).group(1) else bad)('story id of the section equals the script one')
(ok if keys.get('story_id') and ('"%s"' % keys['story_id']) in script else bad)('story id used by the script')
if NAMES:
    names = open(NAMES, encoding='utf-8').read().lower()
    full = 'meshes\\' + vis.lower() if not vis.lower().startswith('meshes') else vis.lower()
    (ok if full in names else bad)('visual %s is a file of the add-on' % full)
    (ok if 'textures\\veh\\veh_btr.dds' in names else bad)('BTR texture is in the add-on')
if BASE:
    model = os.path.join(BASE, 'models', 'vehicles', 'veh_btr_script_u_01.ltx')
    (ok if os.path.isfile(model) else bad)('model config models\\vehicles\\veh_btr_script_u_01.ltx exists in the base configs')
    if os.path.isfile(model):
        mt = open(model, 'rb').read().decode('cp1251', 'replace')
        for need in ('[car_definition]', '[mounted_weapon_definition]'):
            (ok if need in mt else bad)('model config has ' + need)
        wsec = re.search(r'wpn_section\s*=\s*(\S+)', mt).group(1)
        wt = ''
        for r_, _, fs in os.walk(os.path.join(BASE, 'weapons')):
            for fn in fs:
                wt += open(os.path.join(r_, fn), 'rb').read().decode('cp1251', 'replace')
        (ok if '[' + wsec + ']' in wt else bad)('gun section %s exists in the base weapon configs' % wsec)
# ---- no other patch ships these files
mine = []
for dp, _, fs in os.walk(os.path.join(PATCH, 'gamedata')):
    for f in fs:
        mine.append(os.path.relpath(os.path.join(dp, f), os.path.join(PATCH, 'gamedata')).lower())
dups = []
for pn in sorted(os.listdir(os.path.join(REPO, 'patches'))):
    if pn == os.path.basename(PATCH):
        continue
    g = os.path.join(REPO, 'patches', pn, 'gamedata')
    for rel in mine:
        if os.path.isfile(os.path.join(g, rel)):
            dups.append((pn, rel))
(ok if not dups else bad)('no other patch ships a file of this patch %s' % (dups or ''))

# ---- 3. SoC zones
if SOC:
    import soc_spawn
    R = {r['name']: r for r in soc_spawn.load(SOC)}
    block = script[script.index('local HELI_ZONES = {'):script.index('-- SoC actor_ready line')]
    zones = []
    for m in re.finditer(r'\{ x = ([-\d.]+), y = ([-\d.]+), z = ([-\d.]+), shapes = \{(.*?)\} \},?\n', block, re.S):
        shapes = [tuple(float(v) for v in s) for s in re.findall(r'\{ sx = ([-\d.]+), sz = ([-\d.]+), ox = ([-\d.]+), oz = ([-\d.]+) \}', m.group(4))]
        zones.append(((float(m.group(1)), float(m.group(3))), shapes))
    soc_names = ['aes_actor_heli', 'aes_actor_heli2', 'aes_actor_heli1', 'aes_actor_heli3']
    if len(zones) != 4:
        bad('expected 4 helicopter zones in the script, found %d' % len(zones))
    for (pos, shapes), nm in zip(zones, soc_names):
        r = R.get(nm)
        if r is None:
            bad('SoC restrictor %s not found' % nm)
            continue
        if abs(r['pos'][0] - pos[0]) > 0.15 or abs(r['pos'][2] - pos[1]) > 0.15:
            bad('%s position differs' % nm)
        sh = soc_spawn.shapes_of(r)
        want = [(round(s[1][0], 1), round(s[1][8], 1), round(s[1][9], 1), round(s[1][11], 1)) for s in sh]
        have = [(a, b, c, d) for a, b, c, d in shapes]
        if [tuple(round(v, 1) for v in w) for w in want] != [tuple(round(v, 1) for v in h) for h in have]:
            bad('%s boxes differ: SoC %s, script %s' % (nm, want, have))
    ok('4 helicopter zones equal the SoC restrictors')

# ---- 4. flags of the radio
mil = open(os.path.join(REPO, 'patches', 'soc_aes_military', 'gamedata', 'scripts', 'coop_soc_aes_military.script'), 'rb').read().decode('utf-8')
for i in (1, 2, 3):
    f = 'SOC_AESW_DOWN_%d' % i
    (ok if f in script and f in mil else bad)('flag %s is given by the war script and read by the radio' % f)

print('%d problems' % problems)
sys.exit(1 if problems else 0)
