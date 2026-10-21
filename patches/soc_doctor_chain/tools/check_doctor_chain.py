"""Static check of the Guide / Doctor chain (patch soc_doctor_chain). Offline, seconds.
  python -I patches\\soc_doctor_chain\\tools\\check_doctor_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b] [--verify-spot <coop.addon>] [--model-db <gamedata.db1 of the add-on>]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip; run tools\\apply_shared.py first on a scratch copy)
and proves:
  1. the shared edits are in the effective files: system.ltx lists the dialogs / profile / character files and includes the spawn section file,
     task_manager.ltx includes tm_coop_soc_doctor.ltx, the Cordon Guide offers soc_doc_guide_dialog
  2. dialogs: every <next> exists, every phrase is reachable from phrase 0, every <text> has eng + rus, every action / precondition function exists in
     coop_soc_doctor.script, every give_flag is a flag the script reads; the profile lists existing dialogs
  3. tasks: the sections the tick gives exist with title / descr in eng + rus, are not hidden, their marker target is the story id of the spawn section,
     every flag a section reads has a setter somewhere in the effective tree
  4. the Doctor: spawn section (profile, story id, logic file), profile (character + specific character with the same class), model file, logic sections
  5. voice files named by the script exist; text ids used by the scene script exist in eng + rus
  --verify-spot: recomputes the AI node and the game vertex of the Doctor's spot from the add-on's level.ai and the effective all.spawn (needs numpy)
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
model_db = None
for i, a in enumerate(args[1:], 1):
    if a.startswith('--skip='):
        skip = set(a[7:].split(','))
    if a == '--verify-spot' and i + 1 < len(args):
        verify_addon = args[i + 1]
    if a == '--model-db' and i + 1 < len(args):
        model_db = args[i + 1]

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

problems = []


def bad(msg):
    problems.append(msg)
    print('PROBLEM', msg)


def ok(msg):
    print('ok     ', msg)


def read(rel):
    raw = open(tree[rel][1], 'rb').read()
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp1251', errors='replace')


def strings(lang):
    out = {}
    for rel in tree:
        if rel.startswith('configs/text/%s/' % lang) and rel.endswith('.xml'):
            for m in re.finditer(r'<string id="([^"]*)">', read(rel)):
                out[m.group(1)] = rel
    return out


TXT = {'eng': strings('eng'), 'rus': strings('rus')}
SCRIPT = read('scripts/coop_soc_doctor.script')
SCN = read('scripts/coop_scn_soc_doctor.script')
ALLTEXT = {}   # every ltx / xml / script of the effective tree that may set a flag (loaded lazily)


def ltx(rel):
    """{section: {key: value}} of an effective ltx file (no includes followed)."""
    out, cur = {}, None
    for line in read(rel).splitlines():
        line = line.split(';', 1)[0].strip()
        if not line:
            continue
        m = re.match(r'\[([^\]]+)\]', line)
        if m:
            cur = m.group(1).split(':')[0]
            out[cur] = {}
        elif cur is not None and '=' in line:
            k, v = line.split('=', 1)
            out[cur][k.strip()] = v.strip()
    return out


for need in ('configs/gameplay/dialogs_coop_soc_doctor.xml', 'configs/gameplay/npc_profile_soc_doctor.xml', 'configs/gameplay/character_desc_coop_soc_doctor.xml',
             'configs/creatures/spawn_sections_coop_soc_doctor.ltx', 'configs/misc/tm_coop_soc_doctor.ltx', 'configs/text/eng/st_coop_soc_doctor.xml',
             'configs/text/rus/st_coop_soc_doctor.xml', 'configs/scripts/coop_l03_agroprom_underground/soc_cit_doctor.ltx'):
    if need not in tree:
        bad('missing file ' + need)
if problems:
    sys.exit(1)

# ---- 1. the shared edits
sysltx = read('configs/system.ltx')


def sec_line(text, header, key):
    m = re.search(r'^\[' + re.escape(header) + r'\][^\n]*\n(.*?)(?=^\[|\Z)', text, re.M | re.S)
    if not m:
        return []
    km = re.search(r'^' + re.escape(key) + r'\s*=\s*([^\r\n]*)', m.group(1), re.M)
    return [x.strip() for x in km.group(1).split(',')] if km else []


for header, key, item in (('dialogs', 'files', 'dialogs_coop_soc_doctor'), ('profiles', 'files', 'npc_profile_soc_doctor'),
                          ('profiles', 'specific_characters_files', 'character_desc_coop_soc_doctor')):
    (ok if item in sec_line(sysltx, header, key) else bad)('system.ltx [%s] %s lists %s' % (header, key, item))
inc_sp = re.search(r'^#include "creatures\\spawn_sections\.ltx"', sysltx, re.M)
inc_me = re.search(r'^#include "creatures\\spawn_sections_coop_soc_doctor\.ltx"', sysltx, re.M)
(ok if inc_sp and inc_me and inc_me.start() > inc_sp.start() else bad)('system.ltx includes the Doctor spawn section file after spawn_sections.ltx')
(ok if '#include "tm_coop_soc_doctor.ltx"' in read('configs/misc/task_manager.ltx') else bad)('task_manager.ltx includes tm_coop_soc_doctor.ltx')
chars = read('configs/gameplay/character_desc_coop_l01_escape.xml')
gs = chars.find('<specific_character id="esc_smart_terrain_1_stalker_guide"')
ge = chars.find('</specific_character>', gs)
(ok if gs >= 0 and '<actor_dialog>soc_doc_guide_dialog</actor_dialog>' in chars[gs:ge] else bad)('the Cordon Guide offers soc_doc_guide_dialog')

# ---- 2. dialogs
dlg = read('configs/gameplay/dialogs_coop_soc_doctor.xml')
dialogs = {}
for m in re.finditer(r'<dialog id="([^"]+)">(.*?)</dialog>', dlg, re.S):
    dialogs[m.group(1)] = m.group(2)
for d in ('soc_doc_guide_dialog', 'soc_doc_hello_dialog', 'soc_doc_main_dialog'):
    (ok if d in dialogs else bad)('dialog %s exists' % d)
funcs = set(re.findall(r'^function\s+(\w+)', SCRIPT, re.M))
F = dict(re.findall(r'^\s+(\w+)\s*=\s*"([A-Z0-9_]+)"', SCRIPT, re.M))
flags_read = set(F.values())
nphr = 0
for did, body in dialogs.items():
    phrases = {}
    for m in re.finditer(r'<phrase id="([^"]+)">(.*?)</phrase>', body, re.S):
        phrases[m.group(1)] = m.group(2)
    nphr += len(phrases)
    if '0' not in phrases:
        bad('%s: no phrase 0' % did)
        continue
    seen, todo = set(), ['0']
    while todo:
        x = todo.pop()
        if x in seen or x not in phrases:
            continue
        seen.add(x)
        todo += re.findall(r'<next>([^<]+)</next>', phrases[x])
    for pid, ph in phrases.items():
        for n in re.findall(r'<next>([^<]+)</next>', ph):
            if n not in phrases:
                bad('%s: phrase %s points to missing %s' % (did, pid, n))
        if pid not in seen:
            bad('%s: phrase %s is not reachable from 0' % (did, pid))
        t = re.search(r'<text>([^<]*)</text>', ph)
        if t and t.group(1):
            for lang in ('eng', 'rus'):
                if t.group(1) not in TXT[lang]:
                    bad('%s: text %s missing in %s' % (did, t.group(1), lang))
        for a in re.findall(r'<action>([^<]+)</action>', ph) + re.findall(r'<precondition>([^<]+)</precondition>', ph):
            if a == 'dialogs.break_dialog':
                continue
            mod_, fn = a.split('.', 1)
            if mod_ != 'coop_soc_doctor' or fn not in funcs:
                bad('%s: phrase %s calls %s, not a function of coop_soc_doctor.script' % (did, pid, a))
        for fl in re.findall(r'<give_flag>([^<]+)</give_flag>', ph):
            if fl not in flags_read:
                bad('%s: phrase %s gives %s, which the script does not read' % (did, pid, fl))
    for a in re.findall(r'^\s*<precondition>([^<]+)</precondition>', body.split('<phrase_list>')[0], re.M):
        fn = a.split('.', 1)[1]
        (ok if fn in funcs else bad)('%s: dialog precondition %s exists' % (did, a))
ok('dialogs: %d phrases, every <next> exists and is reachable, texts in eng + rus, functions exist' % nphr)
# the voice lines the script names have a phrase text
for fn in re.findall(r'^function\s+(say_\w+)', SCRIPT, re.M):
    if ('coop_soc_doctor.' + fn) not in dlg:
        bad('%s is never called by a dialog' % fn)
for a in set(re.findall(r'coop_soc_doctor\.(say_\w+)', dlg)):
    if a not in funcs:
        bad('say function %s missing' % a)

# ---- profile
prof = read('configs/gameplay/npc_profile_soc_doctor.xml')
sc = read('configs/gameplay/character_desc_coop_soc_doctor.xml')
m = re.search(r'<character id="soc_cit_doctor">\s*<class>([^<]+)</class>', prof)
(ok if m and ('<class>%s</class>' % m.group(1)) in sc else bad)('profile soc_cit_doctor has a specific character of the same class')
for d in re.findall(r'<(?:start_dialog|actor_dialog)>([^<]+)</', sc):
    exists = d in dialogs or d == 'actor_break_dialog' or any(('<dialog id="%s"' % d) in read(r) for r in tree if r.startswith('configs/gameplay/dialogs') and r.endswith('.xml'))
    (ok if exists else bad)('character dialog %s exists' % d)
for tag in ('name', 'bio'):
    t = re.search(r'<%s>([^<]+)</%s>' % (tag, tag), sc).group(1)
    for lang in ('eng', 'rus'):
        (None if t in TXT[lang] else bad('character %s text %s missing in %s' % (tag, t, lang)))
ok('character name / bio texts in eng + rus')
vis = re.search(r'<visual>([^<]+)</visual>', sc).group(1).strip()
(ok if '#include "gameplay\\character_criticals_4.xml"' in sc else bad)('character includes the stock criticals file (as the technician profile)')

# ---- 4. spawn section and logic file
sp = ltx('configs/creatures/spawn_sections_coop_soc_doctor.ltx').get('soc_cit_doctor', {})
(ok if sp.get('character_profile') == 'soc_cit_doctor' else bad)('spawn section: profile soc_cit_doctor')
(ok if sp.get('story_id') == 'soc_cit_doctor' else bad)('spawn section: story id soc_cit_doctor (the task marker)')
logic_rel = 'configs/' + sp.get('custom_data', '').replace('\\', '/').lower()
(ok if logic_rel in tree else bad)('spawn section: custom_data %s exists' % sp.get('custom_data'))
if logic_rel in tree:
    lg = ltx(logic_rel)
    act = lg.get('logic', {}).get('active', '')
    (ok if act in lg else bad)('logic: active section %s exists' % act)
    for s_, kv in lg.items():
        if kv.get('meet') and kv['meet'] not in lg:
            bad('logic: meet section %s missing' % kv['meet'])
(ok if re.search(r'LOGIC_FILE = "scripts\\\\coop_l03_agroprom_underground\\\\soc_cit_doctor\.ltx"', SCRIPT) else bad)('script LOGIC_FILE names the logic file')
(ok if 'story = "soc_cit_doctor"' in SCRIPT and 'section = "soc_cit_doctor"' in SCRIPT else bad)('script creates the section / story id of the spawn section')

# the model
model_rel = vis.replace('\\', '/') + '.ogf'
if model_db is None:
    cand = os.path.join(os.path.dirname(mod), 'addon_unpacked', 'gamedata.db1')
    model_db = cand if os.path.isfile(cand) else None
if model_db:
    sys.path.insert(0, os.path.join(repo, 'tools'))
    import xdb
    f = open(model_db, 'rb')
    names = {e[0].lower().replace('\\', '/') for e in xdb.index(f, 0, os.path.getsize(model_db))}
    want = 'meshes/' + model_rel.lower()
    (ok if want in names else bad)('model %s is in the mod (no .ogf shipped by this patch)' % want)
else:
    print('skip   model check (no add-on db found)')
ship_ogf = [r for r, (fx, p) in tree.items() if fx == 'soc_doctor_chain' and r.endswith('.ogf')]
(ok if not ship_ogf else bad)('this patch ships no .ogf (so no capture ltx can be missing)')

# ---- 3. tasks
tm = ltx('configs/misc/tm_coop_soc_doctor.ltx')
hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))
ids = re.findall(r'\{ id = "(\w+)"', SCRIPT)
(ok if ids == ['soc_doc_meet_task', 'soc_doc_stash_task'] else bad)('the tick gives %s' % ids)
setters = {}


def all_setters():
    if setters:
        return setters
    for rel in tree:
        if rel.startswith('configs/text/'):
            continue
        if not rel.endswith(('.ltx', '.xml', '.script', '.dscript')):
            continue
        t = read(rel)
        for fl in re.findall(r'%[^%\n]*?\+([A-Za-z0-9_]+)', t):
            setters.setdefault(fl.upper(), rel)
        for fl in re.findall(r'<give_flag>([^<]+)</give_flag>', t):
            setters.setdefault(fl.strip().upper(), rel)
        for fl in re.findall(r'give(?:_flag)?\(\s*(?:F\.\w+|"([A-Za-z0-9_]+)")', t):
            if fl:
                setters.setdefault(fl.upper(), rel)
        for fl in re.findall(r'\b(?:story_flags\.give_flag|give)\(\s*"([A-Za-z0-9_]+)"', t):
            setters.setdefault(fl.upper(), rel)
        for fl in re.findall(r'^\s+\w+\s*=\s*"([A-Z0-9_]+)",', t, re.M):
            if rel.endswith('.script'):
                setters.setdefault(fl.upper(), rel + ' (constant)')
    return setters


for tid in ids:
    s = tm.get(tid)
    if s is None:
        bad('tick gives %s: no section' % tid)
        continue
    (ok if tid not in hidden else bad)('%s is not hidden' % tid)
    for k in ('title', 'descr'):
        for lang in ('eng', 'rus'):
            if s.get(k) not in TXT[lang]:
                bad('%s %s=%s missing in %s' % (tid, k, s.get(k), lang))
    tgt = s.get('target', 'nil')
    if tgt != 'nil' and tgt != sp.get('story_id'):
        bad('%s: marker target %s is not the Doctor story id' % (tid, tgt))
    for k, v in s.items():
        if k.startswith('condlist'):
            for fl in re.findall(r'\+([A-Z0-9_]+)', v):
                if fl not in all_setters() and fl not in ('SOC_DOC_CLOSED', 'ESC_FIND_DOCTOR_DONE'):
                    bad('%s: flag %s has no setter in the effective tree' % (tid, fl))
ok('tasks have sections with eng + rus texts, markers resolve, flags have setters')
for fl in sorted(flags_read):
    if fl in ('SOC_DOC_CLOSED', 'ESC_FIND_DOCTOR_DONE'):
        continue
    if fl not in all_setters():
        bad('script reads flag %s: no setter anywhere' % fl)
ok('every flag the script reads has a setter (dialog, script or another patch)')

# ---- 5. voice, scene texts
VOICE_D = re.search(r'VOICE_D = \{([^}]*)\}', SCRIPT).group(1)
for vid in re.findall(r'"(\w+)"', VOICE_D):
    path = 'characters_voice/dialogs/eng/' + ('cit_doctor_hello_dialog_11' if vid == 'h11' else 'cit_doctor_main_dialog_' + vid)
    rel = ('sounds/' + path + '.ogg').lower()
    (ok if rel in tree else bad)('voice file %s' % rel)
for tid in re.findall(r'"(coop_soc_doc_\w+)"', SCN):
    for lang in ('eng', 'rus'):
        if tid not in TXT[lang]:
            bad('scene text %s missing in %s' % (tid, lang))
ok('scene texts exist in eng + rus')
for fl in re.findall(r'ctx\.flag\("([A-Z0-9_]+)"\)', SCN):
    (None if fl in flags_read else bad('scene trigger flag %s is not one of the chain flags' % fl))
ok('scene trigger flags are chain flags')

# ---- optional: the Doctor's spot on the AI mesh
if verify_addon:
    sys.path.insert(0, os.path.join(repo, 'patches', 'level_back', 'tools'))
    import tempfile
    import lc_lib as C
    d = tempfile.mkdtemp()
    lvl = 'coop_l03_agroprom_underground'
    C.extract_level_ai(verify_addon, [lvl], d)
    spawn_path = tree['spawns/all.spawn'][1]
    S = C.X.AllSpawn(open(spawn_path, 'rb').read())
    a = C.AiCache(d).get(lvl)
    m = re.search(r'DOC = \{[^}]*x = ([-0-9.]+), y = ([-0-9.]+), z = ([-0-9.]+), lvid = (\d+), gvid = (\d+)', SCRIPT)
    x, y, z, lvid, gvid = float(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5))
    n, dist = C.nearest_node(a, (x, y, z))
    gv, node = C.own_vertex(S, lvl, n)
    (ok if (n, gv) == (lvid, gvid) and dist < 1.0 else bad)('Doctor spot: node %d (%.2f m away) game vertex %d; script has %d / %d' % (n, dist, gv, lvid, gvid))
    # the SoC knock-out zone and the Doctor's spot are both on the mesh of the level
    m2 = re.search(r'KNOCK = \{ x = ([-0-9.]+), y = ([-0-9.]+), z = ([-0-9.]+)', SCRIPT)
    n2, dist2 = C.nearest_node(a, (float(m2.group(1)), float(m2.group(2)), float(m2.group(3))))
    (ok if dist2 < 1.0 else bad)('the knock-out zone is on the AI mesh (node %d, %.2f m)' % (n2, dist2))

print('\n%d problems' % len(problems))
sys.exit(1 if problems else 0)
