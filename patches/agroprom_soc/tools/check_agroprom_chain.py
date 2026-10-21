"""Static check of the Agroprom / Agroprom underground quest chain (patch agroprom_soc). Offline, seconds.
  python patches\\agroprom_soc\\tools\\check_agroprom_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b]

Builds the EFFECTIVE tree (the mod source, every patch of patches\\ copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the server tick (coop_scn_agroprom_soc.script) gives has a section in the effective task files; every task id given by any
     give_task(...) in the effective Agroprom / underground logic exists; the tasks that are no longer given are given by nobody (except the legacy
     sections that only run for old saves)
  2. every title / description text id of those sections (all branches of the description condlist) exists in eng AND rus, rus has Cyrillic, xml is well formed
  3. every flag the chain reads (task condlists, description / target condlists, tick, restrictors) has a setter in the effective tree
  4. every flag a later level / another patch reads from the Agroprom chain still has a setter, and nothing reads a flag no longer set
  5. the Mole dialog: texts in eng and rus, the PDA archive functions exist, the route flag is given by the last phrase
  6. condlists of the new lines are balanced; story ids used as task targets exist as objects of the level (when the add-on is found)
exit code 1 on any problem"""
import os
import re
import sys
import xml.dom.minidom

sys.stdout.reconfigure(encoding='utf-8')

here = os.path.dirname(os.path.abspath(__file__))
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

_cache = {}


def read(rel):
    if rel not in _cache:
        raw = open(tree[rel][1], 'rb').read()
        try:
            _cache[rel] = raw.decode('utf-8')
        except UnicodeDecodeError:
            _cache[rel] = raw.decode('cp1251', errors='replace')
    return _cache[rel]


problems = []


def bad(s):
    problems.append(s)
    print('PROBLEM', s)


def ok(s):
    print('ok     ', s)


TEXTY = ('.ltx', '.xml', '.script', '.dscript')
code_files = [r for r in tree if r.endswith(TEXTY) and not r.startswith('configs/text/')]

# ---- task sections of the effective tree
sections = {}
for rel in tree:
    if re.match(r'configs/misc/tm_coop_.*\.ltx$', rel):
        cur = None
        for line in read(rel).splitlines():
            line = line.strip()
            m = re.match(r'\[([^\]]+)\]', line)
            if m:
                cur = m.group(1)
                sections[cur] = {'file': rel, 'owner': tree[rel][0]}
            elif cur and '=' in line and not line.startswith(';'):
                k, v = line.split('=', 1)
                sections[cur][k.strip()] = v.strip()
hidden = set()
if 'configs/misc/coop_hidden_tasks.ltx' in tree:
    hidden = set(re.findall(r'(?m)^\s*([a-z0-9_]+)\s*$', read('configs/misc/coop_hidden_tasks.ltx')))

text = {'eng': {}, 'rus': {}}
for rel in tree:
    m = re.match(r'configs/text/(eng|rus)/[^/]+\.xml$', rel)
    if m:
        for sm in re.finditer(r'<string id="([^"]*)">\s*<text>(.*?)</text>', read(rel), re.S):
            text[m.group(1)][sm.group(1)] = sm.group(2)

# ---- 1. tasks
tick = read('scripts/coop_scn_agroprom_soc.script')
chain_ids = re.findall(r'id = "([a-z0-9_]+)"', tick)
for tid in chain_ids:
    if tid not in sections:
        bad('the tick gives task %s but no tm_coop section has it' % tid)
ok('tick gives %d tasks, all have a section: %s' % (len(chain_ids), ', '.join(chain_ids)))

given_by = {}
for rel in code_files:
    if rel.startswith('configs/misc/tm_coop_'):
        continue
    for m in re.finditer(r'give_task\(([a-z0-9_]+)\)', read(rel)):
        given_by.setdefault(m.group(1), []).append(rel)
for tid, rels in sorted(given_by.items()):
    if tid not in sections and tid not in hidden and tid.startswith(('agr_', 'agru_', 'esc_')):
        bad('give_task(%s) in %s: no section, not hidden' % (tid, rels[0]))
NO_LONGER = ('agr_start_talk_to_the_stalker_mole_quest_task', 'agr_start_break_into_a_military_base_quest_task',
             'agr_start_the_destination_is_a_bar_quest_task', 'agru_start_return_to_the_surface_task')
for tid in NO_LONGER:
    where = [r for r in given_by.get(tid, [])]
    # tm files may chain them for old saves only: nothing outside tm files may give them, and the chain tasks may not give them
    if where:
        bad('%s is still given by %s' % (tid, where))
    for cid in chain_ids:
        if re.search(r'give_task\(' + re.escape(tid) + r'\)', ' '.join(v for k, v in sections[cid].items() if isinstance(v, str))):
            bad('chain task %s gives the retired task %s' % (cid, tid))
ok('retired tasks %s are given by nothing (only the legacy tm sections mention them)' % ', '.join(NO_LONGER))
for rel in code_files:
    if 'coop_l03_agroprom' in rel and not rel.startswith('configs/misc/tm_') and 'give_task(' in read(rel):
        bad('%s still calls give_task (a restrictor / walker effect gives the task to ONE player only; the tick does it)' % rel)
ok('no give_task left in the Agroprom / underground logic files')


def text_ids(value):
    """all string ids a (possibly conditional) title / descr value can resolve to"""
    out = []
    for part in re.split(r',(?![^{]*\})', value):
        part = re.sub(r'\{[^}]*\}', '', part).strip()
        part = re.sub(r'%[^%]*%', '', part).strip()
        if part:
            out.append(part)
    return out


# ---- 2. texts
for tid in chain_ids + ['esc_soc_military_documents_task']:
    s = sections.get(tid)
    if not s:
        continue
    for field in ('title', 'descr'):
        for sid in text_ids(s.get(field, '')):
            for lang in ('eng', 'rus'):
                if sid not in text[lang]:
                    bad('%s.%s: string %s missing in %s' % (tid, field, sid, lang))
                elif not text[lang][sid].strip():
                    bad('%s.%s: string %s is empty in %s' % (tid, field, sid, lang))
                elif lang == 'rus' and not re.search('[А-Яа-я]', text[lang][sid]) and not text[lang][sid].startswith('SOS'):
                    bad('string %s has no Cyrillic in rus' % sid)
ok('title and description strings of the chain tasks (all condlist branches) exist in eng and rus')
for rel in tree:
    if re.match(r'configs/text/(eng|rus)/(st_agroprom_soc_chain|st_dialogs_coop_l03_agroprom)\.xml$', rel):
        try:
            xml.dom.minidom.parseString(open(tree[rel][1], 'rb').read())
        except Exception as e:
            bad('xml %s not well formed: %s' % (rel, e))
ok('the two text files are well formed xml')

# ---- 3. flags read by the chain have setters
flag_re = re.compile(r'[+\-]([A-Z][A-Z0-9_]*_(?:INFO|DEAD)|[A-Z][A-Z0-9_]+)\b')
read_flags = set()
for tid in chain_ids + ['esc_soc_military_documents_task']:
    for k, v in sections.get(tid, {}).items():
        if isinstance(v, str) and k.startswith(('condlist', 'descr', 'target')):
            for cond in re.findall(r'\{([^}]*)\}', v):
                read_flags.update(m.upper() for m in re.findall(r'[+\-]([A-Za-z][A-Za-z0-9_]*)', cond))
read_flags.update(re.findall(r'=\s*"([A-Z0-9_]+(?:INFO|DEAD|TAKEN))"', tick))
read_flags = {f for f in read_flags if f == f.upper()}


def setters(flag):
    out = []
    for rel in code_files:
        t = read(rel)
        if flag.lower() not in t.lower():
            continue
        if rel.endswith('.ltx') and not rel.startswith('configs/misc/tm_coop_'):
            if re.search(r'%[^%\n]*\+' + re.escape(flag) + r'\b[^%\n]*%', t, re.I):
                out.append(rel)
        elif rel.endswith('.xml'):
            if re.search(r'<give_flag>\s*' + re.escape(flag) + r'\s*<', t, re.I):
                out.append(rel)
        elif rel == 'scripts/coop_scn_agroprom_soc.script':
            keys = []
            for pair in re.findall(r'(\w+)\s*=\s*"([A-Z0-9_]+)"', t):
                if pair[1].upper() == flag.upper():
                    keys.append(pair[0])
            for key in keys:
                if re.search(r'give\(F\.' + key + r'\)', t):
                    out.append(rel)
                    break
        elif rel.endswith(('.script', '.dscript')):
            if re.search(r'give\w*\(\s*(?:F\.\w+|"' + re.escape(flag) + r'")', t, re.I) or \
               (re.search(r'"' + re.escape(flag) + r'"', t, re.I) and re.search(r'story_flags\.give_flag|give\(', t)):
                out.append(rel)
    return out


for f in sorted(read_flags):
    s = setters(f)
    if not s:
        bad('flag %s is read by the chain but nothing sets it' % f)
    else:
        print('  flag %-80s set by %s' % (f, ', '.join(sorted(set(s))[:3])))
ok('%d flags read by the chain: every one has a setter' % len(read_flags))

# the tick's own gives
for m in re.finditer(r'give\(F\.(\w+)\)', tick):
    fk = m.group(1)
    fm = re.search(r'\b' + fk + r'\s*=\s*"([A-Z0-9_]+)"', tick)
    if not fm:
        bad('tick gives F.%s which is not defined' % fk)

# ---- 4. other levels / patches reading flags of the Agroprom chain
CHAIN_FLAGS = ['AGR_STALKER_HELP_1_INFO', 'AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO', 'AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO',
               'AGR_SMART_TERRAIN_7_STALKER_MOLE_TALK_TO_THE_STALKER_MOLE_STOP_DIALOG_INFO', 'AGR_INVULNERABLE_OFF_INFO', 'AGR_SIRENA_START_INFO',
               'AGR_START_GO_TO_THE_AGROPROM_UNDERGROUND_QUEST_TASK_INFO', 'AGR_THE_ORDER_TO_KILL_STALKER_SPACE_RESTRICTOR_INFO',
               'AGR_THE_ORDER_TO_KILL_MOLE_SPACE_RESTRICTOR_INFO', 'AGR_START_FOLLOW_THE_STALKER_MOLE_QUEST_TASK_THE_AND_INFO',
               'AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO', 'BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO']
for f in CHAIN_FLAGS:
    readers = sorted({rel for rel in code_files if re.search(r'[{ ][+\-!]?' + f + r'\b', read(rel), re.I) and not re.search(r'coop_l03_agroprom|agroprom_soc', rel)})
    readers = [r for r in readers if not r.startswith('scripts/story_flags_table')]
    s = setters(f)
    if readers and not s and f != 'BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO':
        bad('flag %s is read by %s but nothing sets it' % (f, readers[:3]))
    print('  %-82s readers outside Agroprom: %s | setters: %s' % (f, ', '.join(readers[:4]) or '-', ', '.join(sorted(set(s))[:2]) or 'dialog (bar)'))
ok('flags of the Agroprom chain that other levels read still have setters')
bar = [r for r in tree if r == 'configs/gameplay/dialogs_coop_l05_bar.xml'][0]
if not re.search(r'<give_flag>\s*BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO\s*<', read(bar)):
    bad('the Bar dialog no longer gives BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO (the documents task never completes)')
else:
    ok('the Bar dialog (%s) gives the documents-done flag; item agr_safe_container_1 is taken there' % tree[bar][0])

# ---- 5. Mole dialog
dl = read('configs/gameplay/dialogs_coop_l03_agroprom.xml')
phr = set(re.findall(r'coop_pda_phrases\.(\w+)', dl))
pda = read('scripts/coop_pda_phrases.script')
for fn in sorted(phr):
    if not re.search(r'function\s+' + fn + r'\b', pda):
        bad('dialog action coop_pda_phrases.%s missing' % fn)
for sid in re.findall(r'<text>(agr_smart_terrain_7_stalker_mole_[a-z0-9_]+)</text>', dl):
    for lang in ('eng', 'rus'):
        if sid not in text[lang]:
            bad('dialog text %s missing in %s' % (sid, lang))
if 'AGR_SMART_TERRAIN_7_STALKER_MOLE_TALK_TO_THE_STALKER_MOLE_STOP_DIALOG_INFO' not in dl:
    bad('the Mole dialog does not give the route flag')
ok('Mole dialog: functions, texts (eng, rus) and the route flag are there (owner of the dialog file: %s, of the texts: %s)'
   % (tree['configs/gameplay/dialogs_coop_l03_agroprom.xml'][0], tree['configs/text/rus/st_dialogs_coop_l03_agroprom.xml'][0]))

# ---- 6. syntax of the new lines
new_files = [r for r in tree if tree[r][0] in ('agroprom_soc', 'any_player_restrictors') and ('l03_agroprom' in r) and r.endswith('.ltx')]
new_files.append('configs/misc/tm_coop_l01_escape.ltx')
for rel in new_files:
    for i, line in enumerate(read(rel).splitlines(), 1):
        if line.strip().startswith(';'):
            continue
        if line.count('{') != line.count('}') or line.count('%') % 2:
            bad('%s:%d unbalanced braces / percent signs: %s' % (rel, i, line.strip()[:100]))
ok('braces and %% balanced in %d changed config files' % len(new_files))

# story ids of task targets exist on their level (only when the add-on and the spawn reader are around)
try:
    sys.path.insert(0, os.path.join(repo, 'patches', 'stash_markers', 'tools'))
    import gen_safe_boxes as g
    addon = os.path.join(os.path.expanduser('~'), 'Downloads', 'Shadow of COOP 8.0', 'addon_unpacked')
    sids = {}
    for lv, sec, nm, pos, c, st in g.objects(addon):
        if 'agroprom' in lv:
            m = re.search(rb'story_id\s*=\s*([A-Za-z0-9_]+)', c)
            if m:
                sids.setdefault(lv, set()).add(m.group(1).decode('latin1'))
    stash = 'agru_equipment_rucksack_01_case_0000'
    (ok if stash in sids.get('coop_l03_agroprom_underground', set()) else bad)('stash box story id %s is an object of the underground level' % stash)
    for t in ('agr_agru_level_changer',):
        (ok if t in sids.get('coop_l03_agroprom', set()) else bad)('story id %s is an object of the surface level' % t)
except Exception as e:  # noqa: BLE001
    print('note: story id check skipped (%s)' % e)

print()
print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
