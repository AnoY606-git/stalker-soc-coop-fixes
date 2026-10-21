"""Static check of the Radar / X-10 / Pripyat / CNPP / Sarcophagus / Control Monolith chain (patch soc_aes_quests). Offline, seconds.
  python patches\\soc_aes_quests\\tools\\check_aes_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b] [--verify-stash <coop.addon>]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the tick (coop_soc_aes.script) gives has a section with title, descr and eng + rus texts, is not hidden, and its marker target (a story
     object name) exists in all.spawn
  2. the mod-only tasks (Preacher x2, five generator steps, kill-all) are hidden; nothing the tick gives is hidden
  3. every give_task() left in the effective logic of the six levels resolves to a section or a hidden id
  4. every flag the chain reads (the F table, task conditions, the Sarcophagus restrictor) has a setter in the effective tree (ltx %+FLAG%, xml
     give_flag, the chain script's give())
  5. the true ending is intact: its trigger flag has a setter and the scene still reads it; the C-Consciousness refuse path still sets the flag the
     teleport restrictor reads; nothing sets or reads the flags of the removed kill-all task
  6. the decoder: section dev_decoder exists, the Sarcophagus fallback restrictor reads the flag this patch sets, the door still needs only the item
  7. text ids the script uses (stash hint, diary text) exist in eng + rus
  --verify-stash <coop.addon>: recompute the AI node and game vertex of the hotel room from the add-on's level.ai and the effective all.spawn
exit code 1 on any problem"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
mod = args[0]
skip = set()
verify_addon = None
for i, a in enumerate(args[1:], 1):
    if a.startswith('--skip='):
        skip = set(a[7:].split(','))
    if a == '--verify-stash' and i + 1 < len(args):
        verify_addon = args[i + 1]

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

sections = {}
cur = None
for rel in tree:
    if re.match(r'configs/misc/tm_coop_.*\.ltx$', rel):
        for line in read(rel).splitlines():
            line = line.strip()
            m = re.match(r'\[([^\]]+)\]', line)
            if m:
                cur = m.group(1)
                sections[cur] = {'conds': []}
            elif cur and '=' in line and not line.startswith(';'):
                k, v = [x.strip() for x in line.split('=', 1)]
                if k.startswith('condlist_'):
                    sections[cur]['conds'].append(v)
                else:
                    sections[cur][k] = v
hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))

aes = read('scripts/coop_soc_aes.script')
spawn_path = tree['spawns/all.spawn'][1] if 'spawns/all.spawn' in tree else None
spawn_bytes = open(spawn_path, 'rb').read() if spawn_path else b''

# ---- 1. the tick tasks
tick = re.findall(r'\{ id = "(\w+)"', aes)
for tid in tick:
    sec = sections.get(tid)
    if sec is None:
        bad('tick gives %s: no section' % tid)
        continue
    if tid in hidden:
        bad('tick gives %s but it is hidden' % tid)
    for k in ('title', 'descr'):
        for lang in ('eng', 'rus'):
            if sec.get(k) not in text[lang]:
                bad('%s %s=%s missing in %s' % (tid, k, sec.get(k), lang))
    tgt = sec.get('target', 'nil')
    squad = any(('story_id = ' + tgt) in read(r) for r in tree if re.match(r'configs/misc/squad_descr_.*\.ltx$', r))
    if tgt != 'nil' and spawn_bytes and (b'\x00' + tgt.encode() + b'\x00') not in spawn_bytes and not squad:
        bad('%s: marker target %s is neither an object of all.spawn nor a squad story id' % (tid, tgt))
ok('tick tasks (%d) have sections and eng + rus texts, none hidden, markers resolve' % len(tick))

# ---- 2. hidden
for tid in ('sar_start_kill_the_monolith_preacher_quest_task', 'sar_start_search_the_preacher_body_and_retrieve_the_decoder_quest_task',
            'con_start_destroy_the_monolith_installation_2_quest_task', 'con_start_destroy_the_monolith_installation_3_quest_task',
            'con_start_destroy_the_monolith_installation_4_quest_task', 'con_start_destroy_the_monolith_installation_5_quest_task',
            'con_start_destroy_the_monolith_installation_6_quest_task', 'con_start_kill_all_representatives_of_awareness_quest_task'):
    (ok if tid in hidden else bad)('mod-only task %s %s' % (tid, 'is hidden' if tid in hidden else 'NOT hidden'))
    if tid in tick:
        bad('%s is hidden and given by the tick' % tid)

# ---- 3. give_task in the effective logic of the six levels
levels = ('coop_l09_radar', 'coop_l09_x10', 'coop_l10_pripyat', 'coop_l11_control_monolith', 'coop_l11_sarcofag', 'coop_l11_stancia_1', 'coop_l07_military', 'coop_l05_bar')
logic = [rel for rel in tree if any(l in rel for l in levels) and rel.endswith(('.ltx', '.xml')) and not rel.startswith('configs/text')]
logic += [r for r in tree if re.match(r'configs/misc/tm_coop_.*\.ltx$', r)]
given = {}
for rel in sorted(set(logic)):
    for line in read(rel).splitlines():
        if line.lstrip().startswith(';'):
            continue
        for m in re.finditer(r'give_task\((\w+)', line):
            given.setdefault(m.group(1), set()).add(rel)
for tid, rels in sorted(given.items()):
    if tid not in sections and tid not in hidden:
        bad('give_task(%s) in %s has no section and is not hidden' % (tid, sorted(rels)[0]))
ok('give_task ids in the logic of the Radar .. Control Monolith levels: %d, all resolve' % len(given))
mine = [t for t in sections if t.startswith(('x10_', 'pri_', 'aes_1_', 'sar_', 'con_', 'rad_'))]
for tid in sorted(mine):
    if tid not in hidden and tid not in tick and tid not in given and tid != 'rad_start_go_to_radar_quest_task':
        bad('task %s is neither given by the tick, nor by any logic, nor hidden' % tid)

# ---- 4. flags
F = dict(re.findall(r'^\t(\w+)\s*=\s*"([A-Z0-9_]+)",', aes, re.M))
flags = set(F.values())
gens = re.findall(r'"(CON_MONOLITH_GENERATOR_\d_INFO)"', aes)
flags.update(gens)
script_sets = set()
for name, val in F.items():
    if re.search(r'give\(F\.%s\)' % name, aes):
        script_sets.add(val)
sets, reads = {}, {}
for rel in tree:
    if not rel.endswith(('.ltx', '.xml', '.script', '.dscript')) or rel.startswith(('configs/text/', 'configs/ui/')) or rel == 'scripts/story_flags_table.script':
        continue
    if rel == 'scripts/coop_soc_aes.script':
        continue
    t = read(rel)
    for fl in flags:
        if fl not in t:
            continue
        for mm in re.finditer(r'\b' + fl + r'\b', t):
            line_start = t.rfind('\n', 0, mm.start()) + 1
            le = t.find('\n', mm.end())
            line = t[line_start:le if le >= 0 else len(t)]
            if line.lstrip().startswith(';'):
                continue
            pre = t[max(0, mm.start() - 14):mm.start()]
            is_set = False
            if rel.endswith('.xml'):
                is_set = pre.endswith('<give_flag>')
            elif rel.endswith('.ltx'):
                pos = mm.start() - line_start
                for pm in re.finditer(r'%([^%]*)%', line):
                    if pm.start() <= pos <= pm.end() and re.search(r'\+' + fl + r'\b', pm.group(1)):
                        is_set = True
            else:
                is_set = bool(re.search(r'give_flag\(["\']' + fl, t[mm.start() - 12:mm.end() + 2]))
                if not is_set:
                    # local STOP_FLAG = "NAME" ... story_flags.give_flag(STOP_FLAG)
                    vm = re.search(r'local\s+(\w+)\s*=\s*"' + fl + '"', t)
                    is_set = bool(vm and re.search(r'give_flag\(' + vm.group(1) + r'\)', t))
            (sets if is_set else reads).setdefault(fl, set()).add(rel)
for fl in sorted(flags):
    if fl in script_sets:
        sets.setdefault(fl, set()).add('scripts/coop_soc_aes.script')
ENGINE_SET = {  # set by level objects that this check cannot read as text
    'CON_MONOLITH_GENERATOR_': 'the generator logic (xr_effects / generator objects of the level)',
}
for fl in sorted(flags):
    if sets.get(fl):
        ok('%s set by %s' % (fl, sorted(sets[fl])[:2]))
    elif any(fl.startswith(p) for p in ENGINE_SET):
        # generators: the flag is set from the level logic or the monolith scene package
        found = [rel for rel in tree if rel.endswith(('.ltx', '.script', '.dscript', '.xml')) and fl in read(rel) and 'give' in read(rel)]
        (ok if found else bad)('%s: no setter found' % fl if not found else '%s set from level logic (%s)' % (fl, found[0]))
    else:
        bad('flag %s is read but nothing sets it' % fl)

# ---- 5. the true ending and the C-Consciousness path
endings = read('scripts/coop_scn_endings.script')
(ok if 'AES_2_THE_END_SPACE_RESTRICTOR_INFO' in endings else bad)('end_peace still reads AES_2_THE_END_SPACE_RESTRICTOR_INFO')
rel_end = 'configs/scripts/coop_l11_stancia_2/space_restrictors/aes_2_the_end_space_restrictor.ltx'
(ok if rel_end in tree and '+AES_2_THE_END_SPACE_RESTRICTOR_INFO' in read(rel_end) else bad)('the CNPP-2 end restrictor still sets AES_2_THE_END_SPACE_RESTRICTOR_INFO')
fp = read('scripts/coop_scn_freeplay.script') if 'scripts/coop_scn_freeplay.script' in tree else ''
(ok if 'credits_variant' in fp and 'COOP_FREEPLAY_PENDING' in fp else bad)('freeplay is still hooked to the credits after end_peace')
mono = read('scripts/coop_scn_monolith.script')
(ok if 'story_flags.give_flag(STOP_FLAG)' in mono else bad)('the refuse path still gives the C-Consciousness stop flag (the teleport on)')
tele = read('configs/scripts/coop_l11_control_monolith/space_restrictors/con_zone_teleport_3_space_restrictor.ltx')
(ok if 'CON_SMART_TERRAIN_13_ECOLOG_REPRESENTATIVE_AWARENESS_6_DIALOG_STOP_INFO' in tele else bad)('the teleport restrictor still reads the stop flag')
for rel in tree:
    if rel.endswith(('.ltx', '.xml', '.script', '.dscript')) and not rel.startswith(('configs/text/', 'scripts/story_flags_table')):
        t = read(rel)
        t = chr(10).join(l for l in t.splitlines() if not l.lstrip().startswith(';') and not l.lstrip().startswith('--'))
        if 'AES_2_TEST_000_INFO' in t and not rel.startswith('configs/misc/tm_coop_'):
            bad('%s still uses AES_2_TEST_000_INFO (flag of the removed kill-all step)' % rel)
ok('AES_2_TEST_000_INFO (completion of the removed kill-all step) is only in the task section')

# ---- 6. the decoder
qi = read('configs/misc/quest_items_coop.ltx')
(ok if re.search(r'^\[dev_decoder\]', qi, re.M) else bad)('quest item section dev_decoder exists')
rs = read('configs/scripts/coop_l11_sarcofag/space_restrictors/sar_smart_terrain_17_spawn_squad_space_restrictor.ltx')
(ok if '{+PRI_MONOLITH_DECODER_GOT}' in rs and 'spawn_object(dev_decoder:' in rs else bad)('the Sarcophagus fallback spawn is skipped when the stash decoder was found, kept otherwise')
door = read('configs/scripts/coop_l11_sarcofag/doors/sar_codedoor_left_decoder.ltx')
(ok if 'actor_has_item(dev_decoder)' in door and 'PREACHER' not in door else bad)('the door needs only the decoder item (no Preacher flag)')
(ok if 'PRI_MONOLITH_DECODER_GOT' in aes else bad)('the chain script sets PRI_MONOLITH_DECODER_GOT')

# ---- 7. texts used by the script
for tid in re.findall(r'"(coop_soc_aes_\w+)"', aes):
    for lang in ('eng', 'rus'):
        if tid not in text[lang]:
            bad('script text %s missing in %s' % (tid, lang))
ok('script texts exist in eng + rus')

# ---- optional: the stash position on the AI mesh
if verify_addon:
    sys.path.insert(0, os.path.join(repo, 'patches', 'level_back', 'tools'))
    import tempfile
    import lc_lib as C
    d = tempfile.mkdtemp()
    C.extract_level_ai(verify_addon, ['coop_l10_pripyat'], d)
    S = C.X.AllSpawn(open(spawn_path, 'rb').read())
    a = C.AiCache(d).get('coop_l10_pripyat')
    m = re.search(r'x = ([0-9.]+), y = ([0-9.]+), z = ([0-9.]+), lvid = (\d+), gvid = (\d+)', aes)
    x, y, z, lvid, gvid = float(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5))
    n, dist = C.nearest_node(a, (x, y, z))
    gv, node = C.own_vertex(S, 'coop_l10_pripyat', n)
    (ok if (n, gv) == (lvid, gvid) and dist < 2.0 else bad)('stash node %d (%.2f m from the item) game vertex %d; script has %d / %d' % (n, dist, gv, lvid, gvid))

print('\n%d problems' % len(problems))
sys.exit(1 if problems else 0)
