"""Static check of the Yantar / X16 chain (patch soc_yan_x16_quests). Offline, seconds.
  python -I patches\\soc_yan_x16_quests\\tools\\check_yan_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b] [--addon <addon_unpacked>]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the tick (coop_soc_yan.script) gives has a section with title, descr and eng + rus texts in EVERY branch of its condlists
     (description and marker follow the flags), is not hidden, and its map targets are story objects that exist
  2. every give_task() left in the effective Yantar / X16 logic resolves to a section or a hidden id; every retired task is hidden
  3. the Sakharov and Kruglov dialogs: every Lua function, text id (eng + rus) and flag exists, every <next> links, the characters start with them,
     no actor_dialog of any character points to a dialog that does not exist, the replaced level-maker dialogs are gone
  4. every flag the chain reads (task conditions, level logic, dialogs of ANY level, the other SoC patches that read ours) has a setter
  5. the items the script creates exist as sections; Vasiliev's corpse and PDA sections exist with texts
  6. every voice file named in the script ships in the patch
exit code 1 on any problem"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
mod = sys.argv[1]
skip = set()
addon = os.path.join(os.path.expanduser('~'), 'Downloads', 'Shadow of COOP 8.0', 'addon_unpacked')
args = sys.argv[2:]
for i, a in enumerate(args):
    if a.startswith('--skip='):
        skip = set(a[7:].split(','))
    if a == '--addon':
        addon = args[i + 1]

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

# ---- task sections and hidden ids
sections = {}
cur = None
for rel in tree:
    if re.match(r'configs/misc/tm_coop_.*\.ltx$', rel):
        for line in read(rel).splitlines():
            line = line.strip()
            m = re.match(r'\[([^\]]+)\]', line)
            if m:
                cur = m.group(1)
                sections[cur] = {}
            elif cur and '=' in line and not line.startswith(';'):
                k, v = [x.strip() for x in line.split('=', 1)]
                sections[cur][k] = v
hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))

script = read('scripts/coop_soc_yan.script')

# ---- story ids that exist: spawn sections of the effective tree and the level.spawn objects of the add-on
story = set()
for rel in tree:
    if re.match(r'configs/creatures/spawn_sections.*\.ltx$', rel):
        story.update(re.findall(r'(?m)^story_id\s*=\s*(\w+)', read(rel)))
try:
    sys.path.insert(0, os.path.join(repo, 'patches', 'stash_markers', 'tools'))
    import gen_safe_boxes as g
    if os.path.isdir(addon):
        for lv, sec, nm, pos, c, st in g.objects(addon):
            if lv in ('coop_l08_yantar', 'coop_l08_x16', 'coop_l01_escape'):
                story.add(nm)
                mm = re.search(r'story_id\s*=\s*(\w+)', g.custom_data(c, st))
                if mm:
                    story.add(mm.group(1))
except Exception as ex:
    print('(level.spawn not read: %s)' % ex)


def branches(v):
    """every id a condlist value can give: '{+A -B} x, {+C} y, z' -> [x, y, z]"""
    return [re.sub(r'^\{[^}]*\}\s*', '', p.strip()) for p in re.split(r',\s*(?=\{|\w+\s*(?:,|$))', v)]


def flags_of(v):
    return re.findall(r'[+-]([A-Z][A-Z0-9_]+)', v)


# ---- 1. the tick
stages = re.findall(r'\{ id = "(\w+)"', script)
for tid in stages:
    sec = sections.get(tid)
    if sec is None:
        bad('tick gives %s: no section' % tid)
        continue
    if tid in hidden:
        bad('tick gives %s but it is hidden' % tid)
    for k in ('title', 'descr'):
        for br in branches(sec.get(k, '')):
            for lang in ('eng', 'rus'):
                if br not in text[lang]:
                    bad('%s %s branch %s missing in %s' % (tid, k, br, lang))
    for br in branches(sec.get('target', 'nil')):
        if br != 'nil' and br not in story:
            bad('%s target %s is no story object of the mod' % (tid, br))
    for k in sec:
        if k.startswith('condlist') and sec[k].count('{') != sec[k].count('}'):
            bad('%s %s: unbalanced braces' % (tid, k))
ok('tick tasks (%d) have sections, eng + rus texts in every descr / title branch, story targets, none hidden' % len(stages))

# the sections this patch rewrote must keep their ids and have a complete condition
for tid in ('yan_start_talk_to_the_kruglov_quest_task', 'yan_start_infiltrate_the_x16_lab_quest_task', 'x16_start_find_the_installation_quest_task',
            'x16_start_get_out_of_the_lab_task', 'yan_soc_job_task', 'yan_soc_ghost_task', 'yan_soc_guide_task'):
    (ok if tid in stages else bad)('task %s is given by the tick' % tid)
    if not any(k.startswith('condlist') and 'complete' in sections.get(tid, {}).get(k, '') for k in sections.get(tid, {})):
        bad('task %s has no complete condition' % tid)

# ---- 2. give_task in the effective logic of the two levels
logic = [rel for rel in tree if re.search(r'coop_l08_yantar|coop_l08_x16', rel) and rel.endswith(('.ltx', '.xml')) and not rel.startswith('configs/text')]
logic += [r for r in tree if re.match(r'configs/misc/tm_coop_.*\.ltx$', r)]
given = {}
for rel in sorted(set(logic)):
    for m in re.finditer(r'give_task\((\w+)', read(rel)):
        given.setdefault(m.group(1), set()).add(rel)
for tid, rels in sorted(given.items()):
    if tid not in sections and tid not in hidden:
        bad('give_task(%s) in %s has no section and is not hidden' % (tid, sorted(rels)[0]))
retired = ['yan_start_go_to_yantar_quest_task', 'yan_start_take_measurements_1_quest_task', 'yan_start_take_measurements_2_quest_task',
           'yan_start_take_measurements_3_quest_task', 'yan_start_talk_to_the_saharov_quest_task', 'yan_start_configuring_helmets_quest_task',
           'yan_start_talk_to_the_saharov_x16_lab_quest_task', 'x16_start_turn_off_the_switch_1_task', 'x16_start_turn_off_the_switch_2_task',
           'x16_start_turn_off_the_switch_3_task', 'x16_start_turn_off_the_switch_4_task']
for tid in retired:
    (ok if tid in hidden else bad)('retired task %s %s' % (tid, 'is hidden' if tid in hidden else 'NOT hidden'))
    for rel in sorted(given.get(tid, [])):
        # a give_task of a hidden id is ignored by the engine side (client_tasks); report it anyway when it is in LEVEL logic
        if not rel.startswith('configs/misc/tm_coop_'):
            bad('retired task %s is still given by %s' % (tid, rel))
for rel in sorted(set(logic)):
    if rel.endswith('.ltx') and 'coop_l08_' in rel and 'give_task(' in read(rel) and '_sq_' not in rel and not rel.startswith('configs/misc/'):
        print('note   ', rel, 'still calls give_task:', sorted(set(re.findall(r'give_task\((\w+)', read(rel)))))
ok('give_task ids in the Yantar / X16 logic: %d, all resolve; retired tasks are hidden' % len(given))

# ---- 3. the dialogs
dlg = read('configs/gameplay/dialogs_coop_l08_yantar.xml')
fns = {'coop_soc_yan': set(re.findall(r'^function\s+(\w+)', script, re.M))}
fns['coop_soc_yan_semenov'] = set(re.findall(r'^function\s+(\w+)', read('scripts/coop_soc_yan_semenov.script'), re.M)) if 'scripts/coop_soc_yan_semenov.script' in tree else set()
for mod_name in ('coop_pda_phrases',):
    rel = 'scripts/%s.script' % mod_name
    fns[mod_name] = set(re.findall(r'^function\s+(\w+)', read(rel), re.M)) if rel in tree else set()
for did in ('yan_soc_saharov_dialog', 'yan_soc_kruglov_dialog'):
    m = re.search(r'<dialog id="%s">.*?</dialog>' % did, dlg, re.S)
    if not m:
        bad('dialog %s missing' % did)
        continue
    body = m.group(0)
    for mod_name, fn in sorted(set(re.findall(r'<(?:action|precondition)>(\w+)\.(\w+)</', body))):
        if mod_name == 'dialogs':
            continue
        if fn not in fns.get(mod_name, set()):
            bad('dialog function %s.%s MISSING' % (mod_name, fn))
    for tid in sorted(set(re.findall(r'<text>(\w+)</text>', body))):
        for lang in ('eng', 'rus'):
            if tid not in text[lang]:
                bad('dialog text %s missing in %s' % (tid, lang))
    ids = set(re.findall(r'<phrase id="(\w+)">', body))
    for n in set(re.findall(r'<next>(\w+)</next>', body)):
        if n not in ids:
            bad('%s: <next>%s</next> has no phrase' % (did, n))
    # every phrase is reachable from 0
    seen, todo = set(), ['0']
    nxt = {}
    for pm in re.finditer(r'<phrase id="(\w+)">(.*?)</phrase>', body, re.S):
        nxt[pm.group(1)] = re.findall(r'<next>(\w+)</next>', pm.group(2))
    while todo:
        x = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        todo.extend(nxt.get(x, []))
    if seen != ids:
        bad('%s: unreachable phrases %s' % (did, sorted(ids - seen)))
    # the archive functions (say_*) exist for every phrase with a say action
    ok('dialog %s: %d phrases, functions, texts (eng + rus), links and reachability checked' % (did, len(ids)))
chars = read('configs/gameplay/character_desc_coop_l08_yantar.xml')
for cid, d in (('yan_smart_terrain_1_ecolog_saharov', 'yan_soc_saharov_dialog'), ('yan_smart_terrain_1_ecolog_kruglov', 'yan_soc_kruglov_dialog')):
    mm = re.search(r'<specific_character id="%s".*?</specific_character>' % cid, chars, re.S)
    (ok if mm and '<start_dialog>%s</start_dialog>' % d in mm.group(0) else bad)('%s starts with %s' % (cid, d))
defined = set()
for rel in tree:
    if re.match(r'configs/gameplay/(dialogs\w*|dialog\w*)\.xml$', rel):
        defined.update(re.findall(r'<dialog id="(\w+)"', read(rel)))
for rel in tree:
    if re.match(r'configs/gameplay/character_desc_\w+\.xml$', rel):
        t = re.sub(r'<!--.*?-->', '', read(rel), flags=re.S)
        for d in re.findall(r'<(?:actor_dialog|start_dialog)>(\w+)</', t):
            if d not in defined and d not in ('actor_break_dialog', 'agr_smart_terrain_2_1_stalker_mole_start_dialog', 'val_smart_terrain_18_duty_bullet_start_dialog'):
                bad('%s lists dialog %s which is not defined' % (rel, d))
ok('every dialog listed by a character is defined (%d dialogs)' % len(defined))
for d in ('yan_smart_terrain_1_ecolog_kruglov_x16_preparation_dialog', 'yan_smart_terrain_1_ecolog_saharov_talk_to_the_saharov_x16_dialog',
          'yan_smart_terrain_1_ecolog_saharov_talk_to_the_saharov_measurements_dialog', 'yan_smart_terrain_1_ecolog_saharov_give_psi_protection_helmet_dialog',
          'yan_smart_terrain_1_ecolog_saharov_installation_is_disabled_dialog'):
    if d in defined:
        bad('replaced dialog %s is still defined' % d)
    for rel in tree:
        if rel.startswith('configs/gameplay/character_desc_') and d in read(rel):
            bad('%s still lists replaced dialog %s' % (rel, d))
ok('the five level-maker Yantar dialogs are gone')

# ---- 4. flags: read -> must have a setter
interesting = set(re.findall(r'"([A-Z][A-Z0-9_]{6,})"', script))
for tid in stages + ['bar_start_go_to_yantar_quest_task']:
    for k, v in sections.get(tid, {}).items():
        if k in ('descr', 'target') or k.startswith('condlist'):
            interesting.update(flags_of(v))
interesting = set(f for f in interesting if not f.startswith(('ESC_', 'COOP_')) and f != 'NONE')
sets, reads = {}, {}
for rel in tree:
    if not rel.endswith(('.ltx', '.xml', '.script', '.dscript')) or rel.startswith(('configs/text/', 'configs/ui/')) or rel == 'scripts/story_flags_table.script':
        continue
    t = read(rel)
    for fl in interesting:
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
                is_set = bool(re.search(r'give_flag\(["\']' + fl, t[mm.start() - 12:mm.end() + 2]))
            (sets if is_set else reads).setdefault(fl, set()).add(rel)
# flags set through the F tables of the chain scripts (give(F.NAME), give(MEAS[i]) ...)
for srel in ('scripts/coop_soc_yan.script', 'scripts/coop_soc_dv.script', 'scripts/coop_soc_barros.script', 'scripts/coop_scn_agroprom_soc.script', 'scripts/coop_soc_yan_semenov.script'):
    if srel not in tree:
        continue
    s = read(srel)
    for name, val in re.findall(r'\b(\w+)\s*=\s*"([A-Z0-9_]+)",', s):
        if re.search(r'give\(F\.%s\)' % name, s):
            sets.setdefault(val, set()).add(srel)
for lst, var in (('MEAS', 'MEAS'), ('WAITF', 'WAITF')):
    mm = re.search(r'local %s = \{([^}]*)\}' % lst, script, re.S)
    if mm and ('give(%s[' % var) in script:
        for f in re.findall(r'"([A-Z0-9_]+)"', mm.group(1)):
            sets.setdefault(f, set()).add('scripts/coop_soc_yan.script')
for fl in sorted(reads):
    if sets.get(fl):
        ok('%s read by %d file(s), set by %s' % (fl, len(reads[fl]), sorted(sets[fl])[:2]))
    elif fl.endswith('_DEAD'):
        ok('%s read by %d file(s), set by the squad on_death logic (squad_descr)' % (fl, len(reads[fl])))
    else:
        bad('%s is read by %s but nothing sets it' % (fl, sorted(reads[fl])[:3]))
# the flag the Barkeep task of patch bar_soc_quests reads from us
(ok if 'YAN_X16_DOCUMENTS_GAIN' in sets else bad)('YAN_X16_DOCUMENTS_GAIN (read by the Barkeep task and dialog) has a setter: %s' % sorted(sets.get('YAN_X16_DOCUMENTS_GAIN', []))[:2])

# ---- 5. items and spawn sections
items = {}
for rel in tree:
    if re.match(r'configs/(misc|creatures)/[^/]+\.ltx$', rel):
        for m in re.finditer(r'(?m)^\[([\w@]+)\]', read(rel)):
            items[m.group(1)] = rel
for sec in ('yan_psi_detector', 'dev_psi_protection_helmet', 'ecolog_outfit', 'af_cristall_flower', 'lab_x16_documents', 'yan_vasilyev', 'yan_vasilyev_pda', 'x16_stalker_ghost'):
    (ok if sec in items else bad)('section %s %s' % (sec, 'exists (%s)' % items[sec] if sec in items else 'MISSING'))
sp = read('configs/creatures/spawn_sections_coop_l08_yantar.ltx')
(ok if re.search(r'\[yan_vasilyev\]:stalker.*?story_id\s*=\s*yan_vasilyev', sp, re.S) else bad)('Vasiliev has the story id of the task marker')
for tid in ('coop_soc_yan_vasilyev_pda_name', 'coop_soc_yan_vasilyev_pda_descr', 'coop_soc_yan_vasilyev_tip'):
    for lang in ('eng', 'rus'):
        if tid not in text[lang]:
            bad('text %s missing in %s' % (tid, lang))
for p in re.findall(r'"(sim_default_\w+)"|character_profile\s*=\s*(\w+)', sp):
    pass
prof = [x for x in re.findall(r'\[yan_vasilyev\]:stalker\s+character_profile\s*=\s*(\w+)', sp)]
profiles = ''.join(read(r) for r in tree if re.match(r'configs/gameplay/npc_profile.*\.xml$', r))
for pr in prof:
    (ok if re.search(r'<character id="%s"' % pr, profiles) else bad)('profile %s of Vasiliev exists' % pr)

# ---- 6. voice
for kind, var, base in (('s', 'VOICE_S', 'yantar_general_ucheniy_talk_start_'), ('k', 'VOICE_K', 'yantar_help_scientist_')):
    ids = re.search(var + r' = \{([^}]*)\}', script).group(1)
    for i in re.findall(r'"(\d+)"', ids):
        f = 'sounds/characters_voice/dialogs/eng/%s%s.ogg' % (base, i)
        (ok if f in tree else bad)('voice file %s %s' % (f, 'ships' if f in tree else 'MISSING'))

print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
