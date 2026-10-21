"""Static check of the Army Warehouses quest chain (patch soc_mil_quests). Offline, seconds.
  python patches\\soc_mil_quests\\tools\\check_mil_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the tick (coop_soc_mil.script) gives has a section with title, descr and eng + rus texts, and is not hidden
  2. every give_task() left in the effective Military / Bar / Radar logic and task files resolves to a section or a hidden id;
     the mod-only tasks (eight "kill the Duty", fourth sniper, "go to the Radar") are hidden; every other Military task is given by something
  3. the four SoC dialogs: every Lua function, text id (eng + rus), next link and flag exists, the generated xml equals the model,
     the NPCs start with them, nothing lists a dialog that is not defined, the removed level-maker dialogs are gone
  4. every flag of the chain that something reads has a setter in the effective tree (dialog, logic, squad on_death, script)
  5. no Military logic waits for a name with lower case letters (xr_logic treats such a name as an actor info portion, not a story flag:
     nothing would ever give it); the Duty squad and Skull wait for the flag the Skull dialog gives
  6. no reward_money is left on the SoC steps (SoC pays in the dialogs)
exit code 1 on any problem"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import mil_model as M
import gen_dialogs as G

repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
mod = sys.argv[1]
skip = set()
for a in sys.argv[2:]:
    if a.startswith('--skip='):
        skip = set(a[7:].split(','))

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
section_file = {}
cur = None
for rel in sorted(tree):
    if re.match(r'configs/misc/tm_coop_.*\.ltx$', rel):
        for line in read(rel).splitlines():
            line = line.strip()
            m = re.match(r'\[([^\]]+)\]', line)
            if m:
                cur = m.group(1)
                sections[cur] = {}
                section_file[cur] = rel
            elif cur and '=' in line and not line.startswith(';'):
                k, v = [x.strip() for x in line.split('=', 1)]
                sections[cur][k] = v
hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))

# ---- 1. the tick
src = read('scripts/coop_soc_mil.script')
tick = re.findall(r'\{ id = "(\w+)"', src)
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
ok('tick tasks (%d) have sections and eng + rus texts, none hidden' % len(tick))

# ---- 2. give_task
logic = [rel for rel in tree if re.search(r'coop_l07_military|coop_l05_bar|coop_l09_radar', rel) and rel.endswith('.ltx')]
logic += [r for r in tree if re.match(r'configs/misc/tm_coop_.*\.ltx$', r)]
given = {}
for rel in sorted(set(logic)):
    for m in re.finditer(r'give_task\((\w+)', read(rel)):
        given.setdefault(m.group(1), set()).add(rel)
for tid, rels in sorted(given.items()):
    if tid not in sections and tid not in hidden:
        bad('give_task(%s) in %s has no section and is not hidden' % (tid, sorted(rels)[0]))
ok('give_task ids in the Military / Bar / Radar logic and task files: %d, all resolve' % len(given))
for tid in M.HIDDEN:
    (ok if tid in hidden else bad)('mod-only task %s %s' % (tid, 'is hidden' if tid in hidden else 'NOT hidden'))
    if tid in tick:
        bad('hidden task %s is given by the tick' % tid)
for tid in sections:
    if section_file[tid].endswith('tm_coop_l07_military.ltx') and tid not in hidden and tid not in tick and tid not in given:
        bad('task %s is neither given by the tick, nor by any logic, nor hidden' % tid)
ok('every Military task is given by the tick or by logic, or hidden')
for tid in tick:
    if tid in sections and tid.startswith('mil_') and 'reward_money' in sections[tid]:
        bad('%s still has reward_money (SoC pays in the dialogs)' % tid)
ok('no reward_money on the SoC steps')

# ---- 3. dialogs
fns = {'coop_soc_mil': set(re.findall(r'^function\s+(\w+)', src, re.M)),
       'coop_soc_mil_say': set(re.findall(r'^function\s+(\w+)', read('scripts/coop_soc_mil_say.script'), re.M))}
pda = ''
for rel in tree:
    if re.match(r'scripts/coop_pda_phrases\.(d?script)$', rel):
        pda += read(rel)
fns['coop_pda_phrases'] = set(re.findall(r'^function\s+(\w+)', pda, re.M))
dlg_xml = read('configs/gameplay/dialogs_coop_l07_military.xml')
defined = set()
for rel in tree:
    if re.match(r'configs/gameplay/(dialogs\w*|dialog\w*)\.xml$', rel):
        defined.update(re.findall(r'<dialog id="(\w+)"', read(rel)))
for key, d in M.DIALOGS.items():
    m = re.search(r'<dialog id="%s">.*?</dialog>' % d['id'], dlg_xml, re.S)
    if not m:
        bad('dialog %s missing in the effective dialogs_coop_l07_military.xml' % d['id'])
        continue
    body = m.group(0)
    if body.replace('\r\n', '\n').strip() != G.dialog_xml(key).replace('\r\n', '\n').strip():
        bad('dialog %s differs from the model (run tools\\apply_logic.py)' % d['id'])
    for mod_name, fn in sorted(set(re.findall(r'<(?:action|precondition)>(\w+)\.(\w+)</', body))):
        if mod_name == 'dialogs':
            continue
        if fn not in fns.get(mod_name, set()):
            bad('dialog %s: function %s.%s is not defined' % (d['id'], mod_name, fn))
    for tid in sorted(set(re.findall(r'<text>(\w+)</text>', body))):
        for lang in ('eng', 'rus'):
            if tid not in text[lang]:
                bad('dialog %s: text %s missing in %s' % (d['id'], tid, lang))
    ids = set(re.findall(r'<phrase id="(\w+)">', body))
    for n in set(re.findall(r'<next>(\w+)</next>', body)):
        if n not in ids:
            bad('dialog %s: <next>%s</next> has no phrase' % (d['id'], n))
    ok('dialog %s: %d phrases, functions, texts (eng + rus), links, xml equals the model' % (d['id'], len(ids)))
chars = read('configs/gameplay/character_desc_coop_l07_military.xml')
for name, (start, extra) in M.CHARACTERS.items():
    mm = re.search(r'<specific_character id="%s".*?</specific_character>' % name, chars, re.S)
    body = mm.group(0) if mm else ''
    (ok if '<start_dialog>%s</start_dialog>' % start in body else bad)('%s starts with %s' % (name, start))
    for e in extra:
        (ok if '<actor_dialog>%s</actor_dialog>' % e in body else bad)('%s lists %s' % (name, e))
for rel in tree:
    if re.match(r'configs/gameplay/character_desc_\w+\.xml$', rel):
        t = read(rel)
        for d in re.findall(r'<(?:actor_dialog|start_dialog)>(\w+)</', t):
            if d not in defined and d not in ('actor_break_dialog', 'agr_smart_terrain_2_1_stalker_mole_start_dialog', 'val_smart_terrain_18_duty_bullet_start_dialog'):
                bad('%s lists dialog %s which is not defined' % (rel, d))
ok('every dialog listed by a character is defined (%d dialogs)' % len(defined))
for d in M.REMOVED_DIALOGS:
    if d in defined:
        bad('removed dialog %s is still defined' % d)
    for rel in tree:
        if rel.startswith('configs/gameplay/character_desc_') and re.search(r'>' + d + '<', read(rel)):
            bad('%s still lists removed dialog %s' % (rel, d))
ok('the level-maker dialogs of Lukash, Max, Skull and Cap are gone')
if M.MAX_GREETING not in text['eng'] or M.MAX_GREETING not in text['rus']:
    bad('Max greeting text %s missing' % M.MAX_GREETING)
if 'say__' + M.MAX_GREETING not in fns['coop_pda_phrases']:
    ok('note: coop_pda_phrases.say__%s is generated at run time (no static definition)' % M.MAX_GREETING)

# ---- 4. flags
model_flags = [v for k, v in vars(M).items() if isinstance(v, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{8,}', v)]
for lst in (M.DUTY_DEAD, M.SNIPER_DEAD):
    model_flags += lst
model_flags = sorted(set(model_flags))
sets, reads = {}, {}
for rel in tree:
    if not rel.endswith(('.ltx', '.xml', '.script', '.dscript')) or rel.startswith(('configs/text/', 'configs/ui/')) or rel == 'scripts/story_flags_table.script':
        continue
    t = read(rel)
    for fl in model_flags:
        if fl not in t:
            continue
        for mm in re.finditer(r'\b' + fl + r'\b', t):
            line_start = t.rfind('\n', 0, mm.start()) + 1
            le = t.find('\n', mm.end())
            line = t[line_start:le if le >= 0 else len(t)]
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
                is_set = False
            (sets if is_set else reads).setdefault(fl, set()).add(rel)
# flags the chain script sets through its F table
for name, val in re.findall(r'\b(\w+)\s*=\s*"([A-Z0-9_]+)",', src):
    if re.search(r'give\(F\.%s\)' % name, src):
        sets.setdefault(val, set()).add('scripts/coop_soc_mil.script')
if re.search(r'all_of\(DUTY\)\) then give\(F\.DD\)', src):
    sets.setdefault(M.DD, set()).add('scripts/coop_soc_mil.script')
for fl in sorted(reads):
    if sets.get(fl):
        ok('%s read by %d file(s), set by %s' % (fl, len(reads[fl]), sorted(sets[fl])[:2]))
    elif fl in M.DUTY_DEAD or fl in M.SNIPER_DEAD or fl in (M.MD, M.LD, M.SD):
        ok('%s read by %d file(s), set by the squad on_death logic of the simulation (squad_descr)' % (fl, len(reads[fl])))
    elif fl in (M.RADIO, M.RAD_DONE, M.CAP_FAIL):
        ok('%s read by %d file(s), set by a restrictor of another level' % (fl, len(reads[fl])))
    else:
        bad('%s is read by %s but nothing sets it' % (fl, sorted(reads[fl])[:3]))
# squad death flags really exist in squad_descr
sq = read('configs/misc/squad_descr_coop_l07_military.ltx')
for fl in M.DUTY_DEAD + M.SNIPER_DEAD + [M.MD, M.LD, M.SD]:
    (ok if re.search(r'on_death\s*=\s*%\+' + fl + r'%', sq) else bad)('squad on_death sets %s' % fl)

# ---- 5. flag names with lower case in the Military logic
lower = {}
for rel in tree:
    if re.search(r'coop_l07_military|coop_l09_radar', rel) and rel.endswith('.ltx'):
        for m in re.finditer(r'[{ \t]([+\-])([A-Za-z][A-Za-z0-9_]*)', read(rel)):
            n = m.group(2)
            if n != n.upper() and n.upper().startswith(('MIL_', 'RAD_')) and n.upper() == re.sub('_[a-z]+_', lambda x: x.group(0).upper(), n).upper():
                lower.setdefault(n, set()).add(rel)
for n, rels in sorted(lower.items()):
    bad('%s (lower case part) is waited for in %s: not a story flag' % (n, sorted(rels)[0]))
ok('no Military logic waits for a mixed case name')
anim = read('configs/scripts/coop_l07_military/mil_smart_terrain_14_animpoint_duty.ltx')
skull = read('configs/scripts/coop_l07_military/mil_smart_terrain_14_walker_skull.ltx')
n_anim = len(re.findall(r'\{\+' + M.ST + r'\}', anim))
n_skull = len(re.findall(r'\{\+' + M.ST + r'\}', skull))
(ok if n_anim == 8 and n_skull == 1 else bad)('the Duty squad (%d lines) and Skull (%d line) wait for the flag the Skull dialog gives' % (n_anim, n_skull))

print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
