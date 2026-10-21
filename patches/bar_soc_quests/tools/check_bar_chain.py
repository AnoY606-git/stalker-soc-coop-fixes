"""Static check of the Bar / Rostok quest chain (patch bar_soc_quests). Offline, seconds.
  python -I patches\\bar_soc_quests\\tools\\check_bar_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the tick (coop_soc_barros.script) gives has a section with title, descr and eng + rus texts (also every text id inside a descr / target
     condlist), and is not hidden; the mod-only tasks (meeting place x3, the Rostok copy of the Yantar task) are hidden
  2. every give_task() left in the effective Bar / Rostok / Military / Radar / X-10 logic and in the tm files resolves to a section or a hidden id
  3. the Barkeep dialog (X16 hand-in, Scorcher job) and the hunter dialogs: every Lua function, text id (eng + rus), flag and link exists; the characters
     start with them; no character lists a dialog that is not defined; the removed dialogs are gone everywhere
  4. every flag the chain reads (task conditions, level logic, dialogs of ANY level) has a setter in the effective tree
  5. ORDER: the Brain Scorcher job (the mod flag read by the Military / Radar / X-10 / Stancia restrictors) is set ONLY by the Barkeep phrase that follows the
     X16 documents hand-in; nothing else starts it
  6. every voice file named in coop_soc_bar.script ships; the three new Barkeep voice files are in this patch
exit code 1 on any problem"""
import os
import re
import sys

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
            if chr(1082) + chr(1086) + chr(1087) + chr(1080) + chr(1103) in f:       # "copy" in Russian: stray copies in the mod folder, never loaded
                continue
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
                sections[cur] = {}
            elif cur and '=' in line and not line.startswith(';'):
                k, v = [x.strip() for x in line.split('=', 1)]
                sections[cur][k] = v
hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))

# ---- 1. the tick
barros = read('scripts/coop_soc_barros.script')
tick = re.findall(r'\{ id = "(\w+)"', barros)


def text_ids(value):
    """the string ids of a title / descr (plain id or condlist `{cond} id, {cond} id, id`)"""
    ids = []
    for part in value.split(','):
        part = re.sub(r'\{[^}]*\}', '', part).strip()
        if part and part != 'nil':
            ids.append(part)
    return ids


for tid in tick:
    sec = sections.get(tid)
    if sec is None:
        bad('tick gives %s: no section' % tid)
        continue
    if tid in hidden:
        bad('tick gives %s but it is hidden' % tid)
    for k in ('title', 'descr'):
        for lang in ('eng', 'rus'):
            for i in text_ids(sec.get(k, '')):
                if i not in text[lang]:
                    bad('%s %s=%s missing in %s' % (tid, k, i, lang))
ok('tick tasks (%d) have sections and eng + rus texts, none hidden' % len(tick))
for tid in ('bar_start_the_meeting_place_cannot_be_changed_1_quest_task', 'bar_start_the_meeting_place_cannot_be_changed_2_quest_task',
            'bar_start_the_meeting_place_cannot_be_changed_3_quest_task', 'ros_start_go_to_yantar_quest_task'):
    (ok if tid in hidden else bad)('mod-only task %s %s' % (tid, 'is hidden' if tid in hidden else 'NOT hidden'))
# the tm completion of every tick task uses the flag the stage closes with: a stage that stays open after its task is done would give it again
for tid in tick:
    sec = sections.get(tid, {})
    if not any(k.startswith('condlist') for k in sec):
        bad('%s has no completion condlist' % tid)

# ---- 2. give_task in the effective logic
logic = [rel for rel in tree if re.search(r'coop_l0[5-9]_|coop_l05_|coop_l06_|coop_l07_|coop_l09_', rel) and rel.endswith(('.ltx', '.xml'))
         and not rel.startswith('configs/text')]
logic += [r for r in tree if re.match(r'configs/misc/tm_coop_.*\.ltx$', r)]
given = {}
for rel in sorted(set(logic)):
    for m in re.finditer(r'give_task\((\w+)', read(rel)):
        given.setdefault(m.group(1), set()).add(rel)
for tid, rels in sorted(given.items()):
    if tid not in sections and tid not in hidden:
        bad('give_task(%s) in %s has no section and is not hidden' % (tid, sorted(rels)[0]))
ok('give_task ids in the Bar .. Radar logic and tm files: %d, all resolve' % len(given))
# a Bar / Rostok section the tick does not give and that is not hidden must be given by some logic or by another task (otherwise it is dead)
for tid in sections:
    if tid.startswith(('bar_start_', 'bar_soc_', 'ros_')) and '_sq_' not in tid and tid not in hidden and tid not in tick and tid not in given:
        bad('task %s is neither given by the tick, nor by any logic, nor hidden' % tid)
ok('no dead Bar / Rostok story task')

# ---- 3. dialogs
dlg = read('configs/gameplay/dialogs_coop_l05_bar.xml')
bar = read('scripts/coop_soc_bar.script')
hun = read('scripts/coop_soc_hunter.script')
fns = {'coop_soc_bar': set(re.findall(r'^function\s+(\w+)', bar, re.M)), 'coop_soc_hunter': set(re.findall(r'^function\s+(\w+)', hun, re.M))}
for mod_name in ('dialogs_coop_l05_bar', 'dialogs_money', 'dialogs_item', 'coop_pda_phrases'):
    rel = 'scripts/%s.script' % mod_name
    fns[mod_name] = set(re.findall(r'^function\s+(\w+)', read(rel), re.M)) if rel in tree else set()
flags_in_dialogs = set()
for did in ('bar_soc_barmen_start_dialog', 'bar_soc_hunter_start_dialog', 'bar_soc_hunter_quest_dialog', 'bar_soc_hunter_finish_dialog'):
    m = re.search(r'<dialog id="%s">.*?</dialog>' % did, dlg, re.S)
    if not m:
        bad('dialog %s missing' % did)
        continue
    body = m.group(0)
    for mod_name, fn in sorted(set(re.findall(r'<(?:action|precondition)>(\w+)\.(\w+)</', body))):
        if mod_name == 'dialogs':
            continue
        (ok if fn in fns.get(mod_name, set()) else bad)('%s: function %s.%s %s' % (did, mod_name, fn, 'defined' if fn in fns.get(mod_name, set()) else 'MISSING'))
    for tid in sorted(set(re.findall(r'<text>(\w+)</text>', body))):
        for lang in ('eng', 'rus'):
            if tid not in text[lang]:
                bad('%s: text %s missing in %s' % (did, tid, lang))
    ids = set(re.findall(r'<phrase id="(\w+)">', body))
    for n in set(re.findall(r'<next>(\w+)</next>', body)):
        if n not in ids:
            bad('%s: <next>%s</next> has no phrase' % (did, n))
    flags_in_dialogs.update(re.findall(r'<(?:give_flag|has_flag|dont_has_flag)>(\w+)</', body))
    ok('%s: %d phrases, functions, texts (eng + rus) and links checked' % (did, len(ids)))
# the X16 / radar phrases of the Barkeep
m = re.search(r'<dialog id="bar_soc_barmen_start_dialog">.*?</dialog>', dlg, re.S)
body = m.group(0) if m else ''
for pid in ('12', '121', '1211', '1212', '12121', '121211', '13', '131', '1312', '13121', '1313', '1314', '1315', '1316', '132', '1321', '16', '161', '19'):
    (ok if '<phrase id="%s">' % pid in body else bad)('Barkeep phrase %s %s' % (pid, 'present' if '<phrase id="%s">' % pid in body else 'MISSING'))
chars = read('configs/gameplay/character_desc_coop_l05_bar.xml')
for cid, sd, ads in (('bar_smart_terrain_1_stalker_barmen', 'bar_soc_barmen_start_dialog', ()),
                     ('bar_smart_terrain_1_stalker_bad_hunter', 'bar_soc_hunter_start_dialog', ('bar_soc_hunter_quest_dialog', 'bar_soc_hunter_finish_dialog'))):
    mm = re.search(r'<specific_character id="%s".*?</specific_character>' % cid, chars, re.S)
    blk = mm.group(0) if mm else ''
    (ok if '<start_dialog>%s</start_dialog>' % sd in blk else bad)('%s starts with %s' % (cid, sd))
    for a in ads:
        (ok if '<actor_dialog>%s</actor_dialog>' % a in blk else bad)('%s lists %s' % (cid, a))
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
for d in ('bar_smart_terrain_1_stalker_barmen_go_to_military_dialog', 'bar_smart_terrain_1_stalker_informant_the_meeting_place_cannot_be_changed_dialog',
          'bar_smart_terrain_1_stalker_bad_hunter_start_dialog', 'bar_smart_terrain_1_stalker_bad_hunter_find_the_family_gun_quest_dialog',
          'bar_smart_terrain_1_stalker_bad_hunter_find_the_family_gun_quest_idle_dialog'):
    if d in defined:
        bad('removed dialog %s is still defined' % d)
    for rel in tree:
        if rel.startswith('configs/gameplay/character_desc_') and re.search(r'<actor_dialog>%s<' % d, re.sub(r'<!--.*?-->', '', read(rel), flags=re.S)):
            bad('%s still lists removed dialog %s' % (rel, d))
ok('the old go_to_military, informant meeting place and hunter dialogs are gone')

# ---- 4. flags: read -> must have a setter
F_TABLE = dict((v, k) for k, v in re.findall(r'\b(\w+)\s*=\s*"([A-Z0-9_]+)",', barros))
interesting = set(F_TABLE) | flags_in_dialogs
for src in (bar, hun):
    interesting.update(re.findall(r'"([A-Z][A-Z0-9_]{9,})"', src))
interesting = set(f for f in interesting if f.isupper())
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
for val, name in F_TABLE.items():
    if re.search(r'give\(F\.%s\)' % name, barros):
        sets.setdefault(val, set()).add('scripts/coop_soc_barros.script')
# the Dark Valley chain script (patch soc_dv_x18_quests) sets the X18 flags the Barkeep dialog states read
if 'scripts/coop_soc_dv.script' in tree:
    dvs = read('scripts/coop_soc_dv.script')
    for name, val in re.findall(r'\b(\w+)\s*=\s*"([A-Z0-9_]+)",', dvs):
        if re.search(r'give\(F\.%s\)' % name, dvs):
            sets.setdefault(val, set()).add('scripts/coop_soc_dv.script')
sets.setdefault('X16_GHOST_DOCS_TAKEN', set()).add('scripts/coop_scn_yantar_restore.script (local FLAG_DOCS_TAKEN)') \
    if 'scripts/coop_scn_yantar_restore.script' in tree and 'X16_GHOST_DOCS_TAKEN' in read('scripts/coop_scn_yantar_restore.script') else None
for fl in sorted(reads):
    if sets.get(fl):
        ok('%s read by %d file(s), set by %s' % (fl, len(reads[fl]), sorted(sets[fl])[:2]))
    elif fl.endswith('_DEAD'):
        ok('%s read by %d file(s), set by the squad on_death logic of the simulation (squad_descr)' % (fl, len(reads[fl])))
    else:
        bad('%s is read by %s but nothing sets it' % (fl, sorted(reads[fl])[:3]))

# ---- 5. order of the Barkeep jobs
GO = 'BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_MILITARY_STOP_DIALOG_INFO'
setters = sorted(sets.get(GO, set()))
(ok if setters == ['configs/gameplay/dialogs_coop_l05_bar.xml'] else bad)('the Scorcher job flag is set only by the Barkeep dialog: %s' % setters)
mm = re.search(r'<phrase id="1312">.*?</phrase>', body, re.S)
(ok if mm and GO in mm.group(0) and 'BAR_DEACTIVATE_RADAR_START' in mm.group(0) else bad)('phrase 1312 (accepting the Scorcher job) sets the SoC flag and the mod flag')
mm = re.search(r'<phrase id="13">.*?</phrase>', body, re.S)
(ok if mm and 'st_radaroffer' in mm.group(0) else bad)('the Scorcher offer (phrase 13) needs the X16 documents hand-in (state radaroffer)')
mm = re.search(r'<phrase id="1211">.*?</phrase>', body, re.S)
(ok if mm and 'BAR_X16_DOCUMENTS_DONE' in mm.group(0) and 'take_x16_docs' in mm.group(0) else bad)('phrase 1211 takes the documents and sets BAR_X16_DOCUMENTS_DONE together')
mm = re.search(r'<phrase id="17213">.*?</phrase>', body, re.S)
(ok if mm and 'BAR_X16_DOCUMENTS_START' in mm.group(0) else bad)('phrase 17213 (accepting the X16 job) sets BAR_X16_DOCUMENTS_START')
readers = [r for r in tree if r.endswith('.ltx') and GO in read(r) and re.search(r'on_info[^\n]*\{\+' + GO, read(r))]
ok('the Scorcher flag is read by %d restrictor file(s): %s' % (len(readers), ', '.join(sorted(os.path.basename(r) for r in readers))))
# the old chain gate (installation disabled -> Barkeep go_to_military dialog) must not start the Scorcher job any more
for rel in tree:
    if rel.endswith('.xml') and rel.startswith('configs/gameplay/dialogs_') and 'go_to_military_dialog' in read(rel):
        bad('%s still has a go_to_military dialog' % rel)

# ---- 6. voice
voice_ids = re.search(r'VOICE_IDS = \{([^}]*)\}', bar).group(1)
for i in re.findall(r'"(\d+)"', voice_ids):
    f = 'sounds/characters_voice/dialogs/eng/bar_bar_barmen_start_%s.ogg' % i
    (ok if f in tree else bad)('voice file %s %s' % (f, 'ships' if f in tree else 'MISSING'))
for i in ('121', '13121', '1314'):
    f = 'sounds/characters_voice/dialogs/eng/bar_bar_barmen_start_%s.ogg' % i
    (ok if tree.get(f, ('',))[0] == 'bar_soc_quests' else bad)('voice file %s is in patch bar_soc_quests' % i)

print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
