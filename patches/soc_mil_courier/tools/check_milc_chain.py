"""Static proof (no game) of patch soc_mil_courier.

  python -I check_milc_chain.py [--repo <repo root>] [--verify <coop.addon>]

  checks the data fragments in patches\\soc_mil_courier\\data (what apply_shared.py writes) and the patch files:
   1. flags: every flag of the script and of the logic files is in the model, every model flag is used
   2. dialogs: every text exists in eng + rus, every next phrase exists, no phrase is unreachable, every Lua function exists in the script,
      every say function exists, every flag is upper case, every actor dialog of a character exists
   3. characters: spawn sections -> profile -> specific character (same class), names and bios exist, logic files exist
   4. logic files: every patrol path exists in the mod's all.spawn (patches\\darkvalley_restore), no point name of those paths has a flag
      without '=' (utils.parse_waypoint_data aborts on it), every story target is a known story id
   5. tasks: sections, texts, targets, flags, one stage per task in the script
   6. voice: both languages, the model length of every cue is the real length (within 1.5 s)
   7. no em dash, no personal path in any patch file
   --verify <coop.addon>: recomputes the AI node and game vertex of every NPC (needs numpy: run without -I)"""
import os
import re
import struct
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import milc_model as M

patch = os.path.dirname(here)
repo = os.path.dirname(os.path.dirname(patch))
verify_addon = None
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == '--repo':
        repo = os.path.abspath(args[i + 1])
        i += 1
    elif args[i] == '--verify':
        verify_addon = args[i + 1]
        i += 1
    i += 1

problems = []


def bad(s):
    problems.append(s)
    print('PROBLEM', s)


def ok(s):
    print('ok     ', s)


def rd(*a, enc='cp1251'):
    return open(os.path.join(patch, *a), 'rb').read().decode(enc)


script = rd('gamedata', 'scripts', 'coop_soc_milc.script', enc='ascii')
say_script = rd('gamedata', 'scripts', 'coop_soc_milc_say.script', enc='ascii')
mil_script = open(os.path.join(repo, 'patches', 'soc_mil_quests', 'gamedata', 'scripts', 'coop_soc_mil.script'), 'rb').read().decode('utf-8', 'replace')
texts = {l: set(re.findall(r'<string id="([^"]+)">', rd('gamedata', 'configs', 'text', l, 'st_coop_soc_milc.xml'))) for l in ('eng', 'rus')}
mil_texts = set(re.findall(r'<string id="([^"]+)">', open(os.path.join(repo, 'patches', 'soc_mil_quests', 'gamedata', 'configs', 'text', 'eng',
                                                                            'st_coop_soc_mil.xml'), 'rb').read().decode('cp1251')))

# ---- 1. flags
sys.path.insert(0, os.path.join(repo, 'patches', 'soc_mil_quests', 'tools'))
import mil_model as MM          # the flags of soc_mil_quests (read only)
model_flags = set(M.ALL_FLAGS) | {M.BP, M.CP, M.END, M.DONE, M.LD} | {v for k, v in vars(MM).items() if isinstance(v, str) and v.isupper() and v.startswith('MIL_')}     | {f for k, v in vars(MM).items() if isinstance(v, list) for f in v if isinstance(f, str) and f.startswith('MIL_')}
script_flags = set(re.findall(r'"(MIL_[A-Z0-9_]+)"', script))
generated = {f for f in script_flags if re.match(r'MIL_SOC_(MADE|PAID)_', f)}
unknown = sorted(script_flags - model_flags - generated - {'MIL_SOC_PAID_', 'MIL_SOC_MADE_'})
(bad if unknown else ok)('script flags are model flags: %s' % (unknown if unknown else '%d flags' % len(script_flags)))
unused = sorted(f for f in M.ALL_FLAGS if f not in script_flags and f not in M.COOK_DIALOG and f not in M.COOK_DRINK and f not in M.COOK_RG6)
(bad if unused else ok)('every model flag is used by the script (the Chef flags are only dialog flags): %s' % (unused if unused else 'yes'))
logic_dir = os.path.join(patch, 'gamedata', 'configs', 'scripts', 'coop_l07_military')
logic_flags = set()
for f in os.listdir(logic_dir):
    logic_flags |= set(re.findall(r'\+(MIL_[A-Z0-9_]+)', open(os.path.join(logic_dir, f), 'rb').read().decode('ascii')))
(bad if logic_flags - model_flags else ok)('logic file flags are model flags: %s' % (sorted(logic_flags - model_flags) or '%d flags' % len(logic_flags)))
# the flags the logic files wait for are given by the script
not_given = sorted(f for f in logic_flags if script.count('"%s"' % f) == 0 and f not in M.ALL_FLAGS)
(bad if not_given else ok)('every flag of the logic files is given by the script: %s' % (not_given or 'yes'))

# the NPC table of the script is the model
lua_npc = {}
for m in re.finditer(r'^	(\w+) = \{ section = "([^"]+)", story = "([^"]+)", made = "([^"]+)", x = ([-0-9.]+), y = ([-0-9.]+), z = ([-0-9.]+),\s*lv = (\d+), gv = (\d+)',
                     script, re.M):
    lua_npc[m.group(1)] = (m.group(2), m.group(3), float(m.group(5)), float(m.group(6)), float(m.group(7)), int(m.group(8)), int(m.group(9)))
want = {k: (n['section'], n['story'], n['pos'][0], n['pos'][1], n['pos'][2], n['lvid'], n['gvid']) for k, n in M.NPCS.items()}
want['rg6'] = (M.RG6['section'], M.RG6['story'], M.RG6['pos'][0], M.RG6['pos'][1], M.RG6['pos'][2], M.RG6['lvid'], M.RG6['gvid'])
diff = [k for k in want if lua_npc.get(k) != want[k]]
(bad if diff else ok)('NPC table of the script equals the model (section, story id, position, AI node, game vertex): %s' % (diff or '%d objects' % len(want)))
tm_vals = dict(KHUTOR_ZONE=M.KHUTOR_ZONE, KHUTOR_ACTOR=M.KHUTOR_ACTOR)
for name, val in tm_vals.items():
    mm = re.search(r'local %s = \{ ([^}]+) \}' % name, script)
    got = tuple(float(x) for x in mm.group(1).split(',')) if mm else None
    (bad if got != tuple(val) else ok)('%s of the script equals the model' % name)

# ---- 2. dialogs
dialog_files = ['dialogs_l07_cook.xml', 'dialogs_l07_lukash.xml', 'dialogs_l05_voronin.xml']
funcs = {'coop_soc_milc': set(re.findall(r'^function (\w+)\(', script, re.M)), 'coop_soc_mil': set(re.findall(r'^function (\w+)\(', mil_script, re.M)),
         'coop_soc_milc_say': set(re.findall(r'^function (\w+)\(', say_script, re.M))}
mil_say_path = os.path.join(repo, 'patches', 'soc_mil_quests', 'gamedata', 'scripts', 'coop_soc_mil_say.script')
funcs['coop_soc_mil_say'] = set(re.findall(r'^function (\w+)\(', open(mil_say_path, 'rb').read().decode('ascii'), re.M))
all_dialog_ids = set()
n_phr = 0
for fn in dialog_files:
    txt = rd('data', fn)
    for m in re.finditer(r'<dialog id="([^"]+)">(.*?)</dialog>', txt, re.S):
        did, body = m.group(1), m.group(2)
        all_dialog_ids.add(did)
        phrases = {pm.group(1): pm.group(2) for pm in re.finditer(r'<phrase id="([^"]+)">(.*?)</phrase>', body, re.S)}
        reach = {'0'}
        todo = ['0']
        while todo:
            p = todo.pop()
            for n in re.findall(r'<next>([^<]+)</next>', phrases.get(p, '')):
                if n not in phrases:
                    bad('%s: next phrase %s of %s does not exist' % (did, n, p))
                elif n not in reach:
                    reach.add(n)
                    todo.append(n)
        un = sorted(set(phrases) - reach)
        if un:
            bad('%s: unreachable phrases %s' % (did, un))
        for pid, pb in phrases.items():
            n_phr += 1
            t = re.search(r'<text>([^<]+)</text>', pb)
            if t:
                tid = t.group(1)
                if not ((tid in texts['eng'] and tid in texts['rus']) or tid in mil_texts):
                    bad('%s/%s: text %s missing' % (did, pid, tid))
            for ref in re.findall(r'<(?:precondition|action)>([^<]+)</(?:precondition|action)>', pb):
                mod, f = ref.split('.')
                if mod == 'dialogs':
                    continue
                if f not in funcs.get(mod, set()):
                    bad('%s/%s: Lua function %s.%s does not exist' % (did, pid, mod, f))
            for f in re.findall(r'<(?:give_flag|has_flag|dont_has_flag)>([^<]+)<', pb):
                if f != f.upper() or f not in model_flags:
                    bad('%s/%s: flag %s is not an upper case model flag' % (did, pid, f))
        for f in re.findall(r'<(?:has_flag|dont_has_flag)>([^<]+)<', re.sub(r'<phrase_list>.*', '', body, flags=re.S)):
            if f != f.upper() or f not in model_flags:
                bad('%s: dialog flag %s is not an upper case model flag' % (did, f))
        for ref in re.findall(r'<precondition>([^<]+)<', re.sub(r'<phrase_list>.*', '', body, flags=re.S)):
            mod, f = ref.split('.')
            if f not in funcs.get(mod, set()):
                bad('%s: Lua function %s does not exist' % (did, ref))
if not [p for p in problems if 'dialog' in p or '/' in p]:
    ok('dialogs: %d dialogs, %d phrases: texts, next, reachability, Lua functions, flags' % (len(all_dialog_ids), n_phr))

# ---- 3. characters
chars = rd('data', 'characters_l07.xml')
profiles = re.findall(r'<character id="([^"]+)">\s*<class>([^<]+)</class>', rd('data', 'profiles.xml', enc='ascii'))
classes = {m.group(1): m.group(2) for m in re.finditer(r'<specific_character id="([^"]+)".*?<class>([^<]+)</class>', chars, re.S)}
sections = rd('data', 'spawn_sections.ltx', enc='latin-1')
for cid, cls in profiles:
    if classes.get(cid) != cls:
        bad('profile %s: no specific character with class %s' % (cid, cls))
for m in re.finditer(r'^\[([^\]]+)\]:stalker\s*\n(?:(?!\[).*\n)*', sections, re.M):
    blk = m.group(0)
    prof = re.search(r'character_profile\s*=\s*(\S+)', blk).group(1)
    if prof not in [p for p, _ in profiles]:
        bad('section %s: profile %s unknown' % (m.group(1), prof))
    lg = re.search(r'custom_data\s*=\s*scripts\\coop_l07_military\\(\S+)', blk).group(1)
    if not os.path.exists(os.path.join(logic_dir, lg)):
        bad('section %s: logic file %s missing' % (m.group(1), lg))
for cm in re.finditer(r'<specific_character id="([^"]+)".*?</specific_character>', chars, re.S):
    blk = cm.group(0)
    for tag in ('name', 'bio'):
        v = re.search(r'<%s>([^<]+)</%s>' % (tag, tag), blk).group(1)
        if v not in ('GENERATE_NAME_stalker', 'none') and not (v in texts['eng'] and v in texts['rus']):
            bad('character %s: %s %s has no text' % (cm.group(1), tag, v))
    for d in re.findall(r'<(?:start_dialog|actor_dialog)>([^<]+)<', blk):
        if d != 'actor_break_dialog' and d not in all_dialog_ids:
            bad('character %s: dialog %s does not exist' % (cm.group(1), d))
ok('characters: %d profiles, %d sections, names / bios / dialogs / logic files' % (len(profiles), len(re.findall(r':stalker', sections))))
for key, n in M.NPCS.items():
    if ('[%s]:stalker' % n['section']) not in sections:
        bad('no spawn section for %s' % n['section'])
    if not os.path.exists(os.path.join(logic_dir, n['logic'])):
        bad('no logic file for %s' % n['section'])

# ---- 4. paths of the logic files against the mod's all.spawn


def chunks(b):
    i, out = 0, []
    while i < len(b):
        cid, sz = struct.unpack_from('<II', b, i)
        out.append((cid, b[i + 8:i + 8 + sz]))
        i += 8 + sz
    return out


spawn_path = os.path.join(repo, 'patches', 'darkvalley_restore', 'gamedata', 'spawns', 'all.spawn')
ch = dict(chunks(open(spawn_path, 'rb').read()))
patrol = dict(chunks(ch[3]))
PATHS = {}
for cid, pl in chunks(patrol[1]):
    parts = dict(chunks(pl))
    name = parts[0].rstrip(b'\0').decode('latin1')
    pd = dict(chunks(parts[1]))
    pts = []
    for vcid, vpl in chunks(pd[1]):
        vp = dict(chunks(vpl))
        b = vp[1]
        z = b.index(b'\0')
        pts.append(b[:z].decode('latin1'))
    PATHS[name] = pts
used = set()
for f in os.listdir(logic_dir):
    txt = open(os.path.join(logic_dir, f), 'rb').read().decode('ascii')
    for p in re.findall(r'path_(?:walk|look)\s*=\s*(\S+)', txt) + re.findall(r'target\s*=\s*path\|([^,\s]+)', txt):
        used.add(p)
for p in sorted(used):
    if p not in PATHS:
        bad('patrol path %s does not exist in all.spawn' % p)
        continue
    for pn in PATHS[p]:
        for prm in pn.split('|')[1:]:
            if '=' not in prm:
                bad('path %s point %s: flag without "=" (utils.parse_waypoint_data aborts)' % (p, pn))
ok('logic files: %d patrol paths exist, no flag without "=" in their points' % len(used))
sections_all = set(re.findall(r'story_id\s*=\s*(\S+)', sections))
known_story = sections_all | {M.RG6['story']}
spawn_sections_mod = open(os.path.join(repo, 'patches', 'freedom_duty', 'gamedata', 'configs', 'creatures', 'spawn_sections_coop_l07_military.ltx'), 'rb').read().decode('latin-1')
bar_sections = os.path.join(repo, 'patches')
for f in os.listdir(logic_dir):
    txt = open(os.path.join(logic_dir, f), 'rb').read().decode('ascii')
    for s in re.findall(r'target\s*=\s*story\|(\S+)', txt):
        if s not in known_story:
            bad('%s: target story id %s unknown' % (f, s))

# ---- 5. tasks
tm = rd('data', 'tm_tasks.ltx', enc='latin-1')
stage_ids = re.findall(r'\{ id = "([^"]+)"', script)
for t in M.TASKS:
    if ('[%s]' % t['id']) not in tm:
        bad('task section %s missing' % t['id'])
    base = 'st_' + t['id'][:-5]
    for l in ('eng', 'rus'):
        for suf in ('_name', '_descr'):
            if base + suf not in texts[l]:
                bad('text %s missing (%s)' % (base + suf, l))
    story = t['target']
    if story not in known_story and story not in ('mil_smart_terrain_3_freedom_lukash', 'bar_smart_terrain_4_duty_voronin'):
        bad('task %s: target %s unknown' % (t['id'], story))
    for c in t['conds']:
        fl = re.search(r'\+(\w+)', c).group(1)
        if fl not in model_flags:
            bad('task %s: flag %s unknown' % (t['id'], fl))
    if t['id'] not in stage_ids:
        bad('task %s has no stage in the script' % t['id'])
extra = sorted(set(stage_ids) - {t['id'] for t in M.TASKS})
(bad if extra else ok)('tasks: %d sections, texts, targets, flags, one stage each (extra stages: %s)' % (len(M.TASKS), extra))
for f in ('mil_smart_terrain_3_freedom_lukash', 'bar_smart_terrain_4_duty_voronin'):
    if f not in script:
        bad('story id %s is not used by the script' % f)
for story in ('mil_smart_terrain_3_freedom_lukash',):
    if story not in spawn_sections_mod:
        bad('Lukash section missing in the level file')

# ---- 6. voice


def ogg_len(path):
    b = open(path, 'rb').read()
    i = b.find(b'\x01vorbis')
    rate = struct.unpack_from('<I', b, i + 12)[0]
    j = b.rfind(b'OggS')
    gp = struct.unpack_from('<q', b, j + 6)[0]
    return gp / rate


vdir = os.path.join(patch, 'gamedata', 'sounds', 'characters_voice', 'scenario', 'coop_l07_military')
for flag, fn, ms in M.CUES:
    for sub in ('', 'eng'):
        p = os.path.join(vdir, sub, fn + '.ogg')
        if not os.path.exists(p):
            bad('sound %s missing' % p)
            continue
        ln = ogg_len(p) * 1000
        if not (ln <= ms and ms - ln < 1500):
            bad('cue %s (%s): model %d ms, file %.0f ms' % (fn, sub or 'rus', ms, ln))
ok('voice: %d cues in both languages, model lengths match' % len(M.CUES))

# ---- 7. text hygiene
NEEDLE = 'mth' + 'wj'
for dp, dn, fn in os.walk(patch):
    if '__pycache__' in dp:
        continue
    for f in fn:
        if f.endswith(('.ogg',)):
            continue
        raw = open(os.path.join(dp, f), 'rb').read()
        try:
            t = raw.decode('utf-8')
        except UnicodeDecodeError:
            t = raw.decode('cp1251', 'replace')
        if chr(0x2014) in t:
            bad('em dash in ' + os.path.join(dp, f))
        if NEEDLE in t.lower():
            bad('personal name in ' + os.path.join(dp, f))
ok('no em dash, no personal name')

# ---- optional: AI nodes
if verify_addon:
    import tempfile
    sys.path.insert(0, os.path.join(repo, 'patches', 'level_back', 'tools'))
    import lc_lib as C
    d = tempfile.mkdtemp()
    C.extract_level_ai(verify_addon, ['coop_l07_military'], d)
    S = C.X.AllSpawn(open(spawn_path, 'rb').read())
    a = C.AiCache(d).get('coop_l07_military')
    items = [(k, n['pos'], n['lvid'], n['gvid'], False) for k, n in M.NPCS.items()] + [('rg6', M.RG6['pos'], M.RG6['lvid'], M.RG6['gvid'], True)]
    for k, pos, lv, gv, free in items:
        n, dist = C.nearest_node(a, pos)
        g, node = C.own_vertex(S, 'coop_l07_military', n)
        if (n, g) != (lv, gv):
            bad('%s: nearest node %d (%.2f m) game vertex %d, the model has %d / %d' % (k, n, dist, g, lv, gv))
        elif dist > (6.0 if free else 1.0):
            bad('%s: the node is %.2f m from the spot' % (k, dist))
    ok('AI nodes and game vertices of %d objects recomputed from the add-on' % len(items))

print('\n%d problems' % len(problems))
sys.exit(1 if problems else 0)
