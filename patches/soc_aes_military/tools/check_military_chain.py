"""Static check of "Operation Monolith" (patch soc_aes_military). Offline, seconds.
  python patches\\soc_aes_military\\tools\\check_military_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b] [--verify-zones <SoC l12_stancia level.spawn>]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip) and proves:
  1. the task aes_military_task has a section with title, a description in EVERY branch of its descr condlist, a target that is an object of all.spawn,
     eng + rus texts for all of them; it is not hidden (coop_hidden_tasks.ltx) and the section is the only one this patch adds
  2. every flag the task reads has a setter in the script, every flag the script reads from other patches / the level logic has a setter in the tree
  3. every marker has a carrier that exists: smart terrains and the named object are objects of all.spawn, army squads are squads of the effective
     squad_descr_coop_l11_stancia_1.ltx with an army faction that a spawn restrictor of the level really creates; hint texts exist in eng + rus
  4. the radio: every line of the RADIO table ships in this patch in BOTH languages (eng\\ = Steam SoC, rus\\ = Russian SoC, different recordings), nothing else
     ships, no other patch or the mod ships the same sound, the whole patch folder <= 3 MB (3,000,000 bytes)
  5. the map spot type exists in the base map_spots.xml, the news texts exist
  6. the mod's own tasks of tm_coop_l11_stancia_1.ltx are still there byte for byte, the task ids of soc_aes_quests are untouched
  --verify-zones <level.spawn>: every ZONE of the script equals the SoC space_restrictor (position and shapes), the body spot is the SoC soldier
exit code 1 on any problem"""
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')

here = os.path.dirname(os.path.abspath(__file__))
patch_dir = os.path.dirname(here)
repo = os.path.dirname(os.path.dirname(patch_dir))
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
mod = args[0]
skip = set()
verify_spawn = None
for i, a in enumerate(args[1:], 1):
    if a.startswith('--skip='):
        skip = set(a[7:].split(','))
    if a == '--verify-zones' and i + 1 < len(args):
        verify_spawn = args[i + 1]

tree = {}
for db in ('gamedata.db0', 'gamedata.db1'):
    root = os.path.join(mod, db)
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            tree[os.path.relpath(p, root).replace('\\', '/').lower()] = ('mod', p)
for fix in sorted(os.listdir(os.path.join(repo, 'patches'))):
    root = os.path.join(repo, 'patches', fix, 'gamedata')
    if fix in skip or not os.path.isdir(root):
        continue
    for dp, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            tree[os.path.relpath(p, root).replace('\\', '/').lower()] = (fix, p)


def read(rel):
    raw = open(tree[rel][1], 'rb').read()
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp1251', errors='replace')


problems = []


def bad(s):
    problems.append(s)
    print('PROBLEM', s)


def ok(s):
    print('ok     ', s)


text = {'eng': set(), 'rus': set()}
for rel in tree:
    m = re.match(r'configs/text/(eng|rus)/[^/]+\.xml$', rel)
    if m:
        for sm in re.finditer(r'<string id="([^"]*)"', read(rel)):
            text[m.group(1)].add(sm.group(1))

script = read('scripts/coop_soc_aes_military.script')
spawn_path = tree['spawns/all.spawn'][1] if 'spawns/all.spawn' in tree else None
spawn_bytes = open(spawn_path, 'rb').read() if spawn_path else b''


def in_spawn(name):
    return (b'\x00' + name.encode() + b'\x00') in spawn_bytes


# ---- the task section
sections = {}
cur = None
for rel in tree:
    if re.match(r'configs/misc/tm_coop_.*\.ltx$', rel):
        for line in read(rel).splitlines():
            line = line.strip()
            m = re.match(r'\[([^\]]+)\]', line)
            if m:
                cur = m.group(1)
                sections[cur] = {'conds': [], 'file': rel, 'owner': tree[rel][0]}
            elif cur and '=' in line and not line.startswith(';'):
                k, v = [x.strip() for x in line.split('=', 1)]
                if k.startswith('condlist_'):
                    sections[cur]['conds'].append(v)
                else:
                    sections[cur][k] = v
sec = sections.get('aes_military_task')
tid = re.search(r'TASK_ID = "(\w+)"', script).group(1)
(ok if tid == 'aes_military_task' else bad)('the script gives task ' + tid)
read_flags = set()
if sec is None:
    bad('no section aes_military_task')
else:
    ok('section aes_military_task is in ' + sec['file'] + ' (shipped by ' + sec['owner'] + ')')
    if sec['owner'] != 'soc_aes_military':
        bad('the section comes from ' + sec['owner'])
    for k in ('icon', 'title', 'descr', 'target'):
        if k not in sec:
            bad('section has no ' + k)
    for lang in ('eng', 'rus'):
        if sec.get('title') not in text[lang]:
            bad('title %s missing in %s' % (sec.get('title'), lang))
    descr_ids = re.findall(r'(st_\w+_descr)', sec.get('descr', ''))
    for d in descr_ids:
        for lang in ('eng', 'rus'):
            if d not in text[lang]:
                bad('description %s missing in %s' % (d, lang))
    last_branch = sec.get('descr', '').split(',')[-1].strip()
    (ok if not last_branch.startswith('{') else bad)('the last descr branch has no condition (always one text): ' + last_branch)
    ok('%d description branches, eng + rus texts exist' % len(descr_ids))
    tgt = sec.get('target', '')
    for t in re.findall(r'(?:}\s*)?([a-z][a-z0-9_]+)\s*(?:,|$)', tgt):
        (ok if in_spawn(t) else bad)('target %s is an object of all.spawn' % t)
    for f in re.findall(r'[+-]([A-Z0-9_]+)', sec.get('descr', '') + ' ' + ' '.join(sec['conds'])):
        read_flags.add(f)
    hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))
    (ok if 'aes_military_task' not in hidden else bad)('the task is not hidden')

# ---- flags
setters = set(re.findall(r'give\(F\.(\w+)\)', script))
fmap = dict(re.findall(r'^\t(\w+)\s*= "([A-Z0-9_]+)"', script[script.index('local F = {'):script.index('-- SoC positions')], re.M))
set_names = {fmap[k] for k in setters if k in fmap}
for f in sorted(read_flags):
    (ok if f in set_names else bad)('flag %s of the task has a setter in the script' % f)
for k, f in fmap.items():
    if not f.startswith('SOC_AESM_'):
        # read-only flags of other patches / the level logic
        found = False
        for rel in tree:
            if rel.endswith(('.ltx', '.script', '.dscript', '.xml')) and not rel.endswith('coop_soc_aes_military.script'):
                try:
                    if ('+' + f) in read(rel) or ('give(' + f) in read(rel) or ('"' + f + '"') in read(rel):
                        found = True
                        break
                except Exception:
                    pass
        (ok if found else bad)('flag %s (read only) is set / used by the mod or another patch' % f)
ok('flags checked')

# ---- markers
spots = re.findall(r'\{ key = "(\w+)",\s*hint = "(\w+)",\s*(smart|squad|obj) = "(\w+)"', script)
(ok if len(spots) == 12 else bad)('12 markers in the script (%d)' % len(spots))
squad_text = read('configs/misc/squad_descr_coop_l11_stancia_1.ltx')
logic = ''
for rel in tree:
    if rel.startswith('configs/scripts/coop_l11_stancia_1/space_restrictors/'):
        logic += read(rel)
for key, hint, kind, ref in spots:
    for lang in ('eng', 'rus'):
        if hint not in text[lang]:
            bad('hint %s missing in %s' % (hint, lang))
    if kind == 'squad':
        m = re.search(r'\[' + re.escape(ref) + r'\]:online_offline_group(.*?)(?=\n\[|\Z)', squad_text, re.S)
        if not m:
            bad('marker %s: squad %s is not in squad_descr_coop_l11_stancia_1.ltx' % (key, ref))
            continue
        if 'faction = army' not in m.group(1) or ('story_id = ' + ref) not in m.group(1):
            bad('marker %s: squad %s is not an army squad with its own story id' % (key, ref))
        if ('create_squad(' + ref + ':') not in logic:
            bad('marker %s: no spawn restrictor of the level creates squad %s' % (key, ref))
    else:
        (ok if in_spawn(ref) else bad)('marker %s: carrier %s is an object of all.spawn' % (key, ref))
ok('markers checked (%d)' % len(spots))
(ok if 'green_location' in open(os.path.join(os.path.dirname(mod), 'source_base', 'xrmpe_patch', 'configs', 'ui', 'map_spots.xml'), encoding='utf-8', errors='replace').read() else bad)(
    'map spot type green_location exists in the base map_spots.xml')
for t in ('coop_soc_aesm_news_name', 'coop_soc_aesm_news_text'):
    for lang in ('eng', 'rus'):
        if t not in text[lang]:
            bad('news text %s missing in %s' % (t, lang))
ok('news texts exist')

# ---- radio
block = script[script.index('RADIO = {'):script.index('local RADIO_DIR')]
lines = [l.replace('\\\\', '/') for l in re.findall(r'"(aes[A-Za-z0-9_\\]*)"', block)]
shipped = {}
total = 0
root = os.path.join(patch_dir, 'gamedata', 'sounds', 'characters_voice', 'scenario', 'aes')
for dp, _, fs in os.walk(root):
    for f in fs:
        rel = os.path.relpath(os.path.join(dp, f), root).replace('\\', '/')
        shipped[rel] = os.path.getsize(os.path.join(dp, f))
        total += shipped[rel]
for lang in ('eng', 'rus'):
    for l in lines:
        if lang + '/' + l + '.ogg' not in shipped:
            bad('radio line %s is not shipped in %s' % (l, lang))
for s_ in shipped:
    if s_.split('/')[0] not in ('eng', 'rus') or s_[:-4].split('/', 1)[1] not in lines:
        bad('shipped sound %s is not used by the RADIO table' % s_)
    rel = 'sounds/characters_voice/scenario/aes/' + s_
    if tree[rel.lower()][0] != 'soc_aes_military':
        bad('sound %s is also shipped by %s' % (rel, tree[rel.lower()][0]))
    head = open(os.path.join(root, *s_.split('/')), 'rb').read(4)
    if head != b'OggS':
        bad('sound %s is not an ogg' % s_)
for l in set(lines):
    if shipped.get('eng/' + l + '.ogg') == shipped.get('rus/' + l + '.ogg') and \
            open(os.path.join(root, 'eng', *l.split('/')) + '.ogg', 'rb').read() == open(os.path.join(root, 'rus', *l.split('/')) + '.ogg', 'rb').read():
        bad('line %s is the same file in eng and rus (the two recordings differ in the SoC)' % l)
patch_total = 0
for dp, _, fs in os.walk(os.path.join(patch_dir, 'gamedata')):
    for f in fs:
        patch_total += os.path.getsize(os.path.join(dp, f))
(ok if patch_total <= 3000000 else bad)('patch size %.2f MB, radio %.2f MB (limit 3 MB for the whole patch)' % (patch_total / 1e6, total / 1e6))
ok('%d radio lines x 2 languages, all shipped' % len(set(lines)))
triggers = re.findall(r'\{ key = "(\w+)",\s*zone = (nil|"\w+")', block)
zones = set(re.findall(r'^\t(\w+)\s*= \{ x = ', script[script.index('local ZONE = {'):script.index('-- the radio:')], re.M))
for k, z in triggers:
    if z != 'nil' and z.strip('"') not in zones:
        bad('radio trigger %s names an unknown zone %s' % (k, z))
(ok if len({k for k, _ in triggers}) == len(triggers) else bad)('radio trigger keys are unique (the per-player flag uses them)')
for k, _ in triggers:
    if len('SOC_AESM_R_' + 'X' * 24 + '_' + k) > 60:
        bad('flag name of trigger %s too long' % k)
ok('%d radio triggers, zones exist' % len(triggers))
(ok if 'voice_lang()' in script and 'RADIO_DIR .. voice_lang()' in script else bad)('the script plays the line of the voice language of the player')

# ---- the mod's own tasks are intact
mine = tree['configs/misc/tm_coop_l11_stancia_1.ltx'][1]
orig = os.path.join(mod, 'gamedata.db0', 'configs', 'misc', 'tm_coop_l11_stancia_1.ltx')
a = open(orig, 'rb').read()
b = open(mine, 'rb').read()
(ok if b.startswith(a.rstrip(b'\r\n')) else bad)('tm_coop_l11_stancia_1.ltx starts with the mod file byte for byte')
(ok if 'aes_1_start_go_to_sarcofag_quest_task' in sections else bad)('the mod task aes_1_start_go_to_sarcofag_quest_task is still there')
aes_ids = re.findall(r'\{ id = "(\w+)"', read('scripts/coop_soc_aes.script')) if 'scripts/coop_soc_aes.script' in tree else []
(ok if 'aes_military_task' not in aes_ids else bad)('soc_aes_quests does not use the id aes_military_task')
for dup in ('scripts/coop_soc_aes_military.script', 'scripts/coop_scn_soc_aes_military.script', 'configs/text/eng/st_coop_soc_aes_military.xml', 'configs/text/rus/st_coop_soc_aes_military.xml'):
    (ok if tree[dup][0] == 'soc_aes_military' else bad)('%s is only in this patch' % dup)
ok('own and other patches checked')

# ---- the SoC zones
if verify_spawn:
    sys.path.insert(0, here)
    import soc_spawn
    R = soc_spawn.load(verify_spawn)
    by = {r['name']: r for r in R}
    names = {
        'actor_ready': 'aes_space_restrictor_actor_ready', 'zabor': 'aes_space_restrictor_zabor', 'btr': 'aes_space_restrictor_btr',
        'gate': 'aes_space_restrictor_gate', 'momsters': 'aes_space_restrictor_momsters', 'heli1': 'aes_actor_heli', 'road': 'aes_space_restrictor_road',
        'ambush5': 'aes_space_restrictor_ambush_0001', 'bridge': 'aes_space_restrictor', 'ambush1': 'aes_space_restrictor_ambush',
        'road_sound2': 'aes_space_restrictor_road_sound_0000', 'road2': 'aes_space_restrictor_road2', 'ambush2': 'aes_space_restrictor_0000',
        'btr_ambush': 'aes_space_restrictor_btr_ambush', 'road_sound1': 'aes_space_restrictor_road_sound', 'actor_sound': 'aes_space_restrictor_actor_sound',
    }
    zblock = script[script.index('local ZONE = {'):script.index('-- the radio:')]
    n = 0
    for zk, soc in names.items():
        if zk not in zones:
            continue    # a zone without a radio trigger is not in the script (see NOTES.md)
        r = by.get(soc)
        if r is None:
            bad('SoC restrictor %s not found' % soc)
            continue
        m = re.search(r'^\t' + zk + r'\s*= \{ x = (-?[0-9.]+), y = (-?[0-9.]+), z = (-?[0-9.]+), shapes = \{(.*)\} \},?\r?$', zblock, re.M)
        if not m:
            bad('zone %s not in the script' % zk)
            continue
        pos = tuple(float(m.group(i)) for i in (1, 2, 3))
        good = all(abs(pos[i] - r['pos'][i]) < 0.06 for i in range(3))
        shp = soc_spawn.shapes_of(r)
        want = []
        for s in shp:
            if s[0] == 'sph':
                want.append((round(s[2], 1), round(s[1][0], 1), round(s[1][1], 1), round(s[1][2], 1)))
            else:
                mm = s[1]
                want.append((round(mm[0], 1), round(mm[4], 1), round(mm[8], 1), round(mm[9], 1), round(mm[10], 1), round(mm[11], 1)))
        got = []
        for sm in re.finditer(r'\{ (?:r = ([0-9.]+)|sx = ([0-9.]+), sy = ([0-9.]+), sz = ([0-9.]+)), ox = (-?[0-9.]+), oy = (-?[0-9.]+), oz = (-?[0-9.]+) \}', m.group(4)):
            if sm.group(1) is not None:
                got.append((float(sm.group(1)), float(sm.group(5)), float(sm.group(6)), float(sm.group(7))))
            else:
                got.append(tuple(float(sm.group(i)) for i in (2, 3, 4, 5, 6, 7)))
        if not good or len(got) != len(want) or any(max(abs(x - y) for x, y in zip(g, w)) > 0.06 for g, w in zip(got, want)):
            bad('zone %s differs from the SoC restrictor %s' % (zk, soc))
        else:
            n += 1
    ok('%d zones equal the SoC restrictors (position, shapes)' % n)
    sold = by.get('aes_stalker_0000')
    bm = re.search(r'BODY\s*= \{ x = (-?[0-9.]+),\s*y = (-?[0-9.]+),\s*z = (-?[0-9.]+)', script)
    (ok if sold and all(abs(float(bm.group(i + 1)) - sold['pos'][i]) < 0.06 for i in range(3)) else bad)('BODY is the SoC soldier aes_stalker_0000 (known_info aes_get_soldier_map)')
    (ok if sold and 'aes_get_soldier_map' in sold['pl'].decode('latin1') else bad)('the SoC soldier really carries the info aes_get_soldier_map')
    sf = by.get('aes_space_restrictor_task_0000')
    sm_ = re.search(r'SARC\s*= \{ x = (-?[0-9.]+),\s*y = (-?[0-9.]+),\s*z = (-?[0-9.]+)', script)
    (ok if sf and all(abs(float(sm_.group(i + 1)) - sf['pos'][i]) < 0.06 for i in range(3)) else bad)('SARC is the SoC aes_found_sarcofag restrictor')
    (ok if sf and 'aes_found_sarcofag' in sf['pl'].decode('latin1') else bad)('that restrictor really sets aes_found_sarcofag')

print('\n%d problems' % len(problems))
sys.exit(1 if problems else 0)
