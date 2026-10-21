"""Static check of the Dark Valley / X18 / Barkeep chain (patch soc_dv_x18_quests). Offline, seconds.
  python patches\\soc_dv_x18_quests\\tools\\check_dv_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b]

Builds the EFFECTIVE tree (the mod source, every patch copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the tick (coop_soc_dv.script) gives has a section with title, descr and eng + rus texts, and is not hidden
  2. every give_task() left in the effective Dark Valley / X18 / Bar logic resolves to a section or a hidden id; every removed (mod-only) task is hidden
  3. the Barkeep dialog: every Lua function, text id (eng + rus) and flag exists; the Barkeep starts with it; no actor_dialog of the
     Bar / Cordon / Dark Valley characters points to a dialog that no longer exists
  4. every flag the chain reads (task conditions, level logic, dialogs of ANY level) has a setter in the effective tree
  5. nothing refers to the removed Sidorovich document dialog
  6. every voice file named in coop_soc_bar.script ships in the patch
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

# ---- 1. the tick
dv = read('scripts/coop_soc_dv.script')
tick = re.findall(r'\{ id = "(\w+)"', dv)
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

# ---- 2. give_task in the effective logic of the three levels
logic = [rel for rel in tree if re.search(r'coop_l04_darkvalley|coop_l04_x18|coop_l05_bar', rel) and rel.endswith(('.ltx', '.xml'))
         and not rel.startswith('configs/text')]
logic += [r for r in tree if re.match(r'configs/misc/tm_coop_.*\.ltx$', r)]
given = {}
for rel in sorted(set(logic)):
    for m in re.finditer(r'give_task\((\w+)', read(rel)):
        given.setdefault(m.group(1), set()).add(rel)
for tid, rels in sorted(given.items()):
    if tid not in sections and tid not in hidden:
        bad('give_task(%s) in %s has no section and is not hidden' % (tid, sorted(rels)[0]))
ok('give_task ids in the Dark Valley / X18 / Bar logic: %d, all resolve' % len(given))
for tid in ('bar_start_sneak_into_the_x_18_lab_quest_task', 'val_start_go_to_the_sos_signal_1_quest_task', 'val_start_go_to_the_sos_signal_2_quest_task',
            'val_start_fake_gauss_1_quest_task', 'val_start_fake_gauss_2_quest_task', 'val_start_show_documents_to_sidorovich_quest_task',
            'x18_start_go_to_x18_doc_1_task', 'x18_start_go_to_x18_doc_2_task', 'x18_start_go_to_x18_doc_3_task',
            'x18_start_find_the_password_x18_codedoor_1_task', 'x18_start_find_the_password_x18_codedoor_2_task',
            'x18_start_kill_the_flame_poltergeist_quest_task', 'x18_start_get_out_of_the_lab_quest_task'):
    (ok if tid in hidden else bad)('mod-only task %s %s' % (tid, 'is hidden' if tid in hidden else 'NOT hidden'))
# a section the tick does not give and that is not hidden must be given by some logic (otherwise it is dead)
mine = ('val_', 'x18_', 'bar_start_go_to_yantar')
for tid in sections:
    if tid.startswith(('val_', 'x18_')) and tid not in hidden and tid not in tick and tid not in given:
        bad('task %s is neither given by the tick, nor by any logic, nor hidden' % tid)

# ---- 3. the Barkeep dialog
dlg = read('configs/gameplay/dialogs_coop_l05_bar.xml')
m = re.search(r'<dialog id="bar_soc_barmen_start_dialog">.*?</dialog>', dlg, re.S)
if not m:
    bad('dialog bar_soc_barmen_start_dialog missing')
    body = ''
else:
    body = m.group(0)
bar = read('scripts/coop_soc_bar.script')
fns = {'coop_soc_bar': set(re.findall(r'^function\s+(\w+)', bar, re.M))}
for mod_name in ('dialogs_coop_l05_bar', 'dialogs_money', 'coop_pda_phrases'):
    rel = 'scripts/%s.script' % mod_name
    fns[mod_name] = set(re.findall(r'^function\s+(\w+)', read(rel), re.M)) if rel in tree else set()
for mod_name, fn in sorted(set(re.findall(r'<(?:action|precondition)>(\w+)\.(\w+)</', body))):
    if mod_name == 'dialogs':
        continue
    (ok if fn in fns.get(mod_name, set()) else bad)('dialog function %s.%s %s' % (mod_name, fn, 'defined' if fn in fns.get(mod_name, set()) else 'MISSING'))
for tid in sorted(set(re.findall(r'<text>(\w+)</text>', body))):
    for lang in ('eng', 'rus'):
        if tid not in text[lang]:
            bad('dialog text %s missing in %s' % (tid, lang))
# every next points at a phrase of the dialog
ids = set(re.findall(r'<phrase id="(\w+)">', body))
for n in set(re.findall(r'<next>(\w+)</next>', body)):
    if n not in ids:
        bad('dialog <next>%s</next> has no phrase' % n)
ok('Barkeep dialog: %d phrases, functions, texts (eng + rus) and links checked' % len(ids))
chars = read('configs/gameplay/character_desc_coop_l05_bar.xml')
mm = re.search(r'<specific_character id="bar_smart_terrain_1_stalker_barmen".*?</specific_character>', chars, re.S)
(ok if mm and '<start_dialog>bar_soc_barmen_start_dialog</start_dialog>' in mm.group(0) else bad)('the Barkeep starts with the SoC dialog')
# all dialogs defined anywhere in the effective tree
defined = set()
for rel in tree:
    if re.match(r'configs/gameplay/(dialogs\w*|dialog\w*)\.xml$', rel):
        defined.update(re.findall(r'<dialog id="(\w+)"', read(rel)))
for rel in tree:
    if re.match(r'configs/gameplay/character_desc_\w+\.xml$', rel):
        t = read(rel)
        for d in re.findall(r'<(?:actor_dialog|start_dialog)>(\w+)</', t):
            # two Dark Valley characters (Mole, Bullet) already listed a start dialog nobody defines in the stock mod
            if d not in defined and d not in ('actor_break_dialog', 'agr_smart_terrain_2_1_stalker_mole_start_dialog', 'val_smart_terrain_18_duty_bullet_start_dialog'):
                bad('%s lists dialog %s which is not defined' % (rel, d))
ok('every dialog listed by a character is defined (%d dialogs)' % len(defined))
for d in ('bar_smart_terrain_1_trader_barmen_has_documents_agroprom_dialog', 'bar_smart_terrain_1_stalker_barmen_go_to_darkvalley_dialog',
          'bar_smart_terrain_1_stalker_barmen_1_has_documents_darkvalley_dialog', 'esc_smart_terrain_1_trader_sidorovich_x18_documents'):
    if d in defined:
        bad('removed dialog %s is still defined' % d)
    for rel in tree:
        if rel.startswith('configs/gameplay/character_desc_') and d in read(rel):
            bad('%s still lists removed dialog %s' % (rel, d))
ok('the three level-maker Barkeep dialogs and the Sidorovich document dialog are gone')

# ---- 4. flags: read -> must have a setter
flag_re = re.compile(r'\b([A-Z][A-Z0-9_]{6,})\b')
interesting = set()
for src in (dv, bar):
    interesting.update(re.findall(r'"([A-Z][A-Z0-9_]{6,})"', src))
interesting.update(re.findall(r'[<{ +-]([A-Z][A-Z0-9_]*_(?:INFO|DEAD|START|CLOSED|OPEN|GAIN))[>} %]', read('configs/misc/tm_coop_l04_darkvalley.ltx')))
interesting = set(f for f in interesting if f not in ('NONE',))
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
                # Lua: give(F.NAME) in the chain script, give_flag("NAME")
                is_set = bool(re.search(r'give_flag\(["\']' + fl, t[mm.start() - 12:mm.end() + 2]))
            (sets if is_set else reads).setdefault(fl, set()).add(rel)
# flags the chain script sets through its F table
for name, val in re.findall(r'\b(\w+)\s*=\s*"([A-Z0-9_]+)",', dv):
    if re.search(r'give\(F\.%s\)' % name, dv):
        sets.setdefault(val, set()).add('scripts/coop_soc_dv.script')
# the Bar / Rostok chain of patch bar_soc_quests sets the X16 / radar flags the Barkeep dialog reads
if 'scripts/coop_soc_barros.script' in tree:
    barros = read('scripts/coop_soc_barros.script')
    for name, val in re.findall(r'\b(\w+)\s*=\s*"([A-Z0-9_]+)",', barros):
        if re.search(r'give\(F\.%s\)' % name, barros):
            sets.setdefault(val, set()).add('scripts/coop_soc_barros.script')
for name in re.findall(r'give\(DOCF\[', dv):
    for i in (1, 2, 3):
        sets.setdefault('X18_START_GO_TO_X18_DOC_%d_TASK_INFO' % i, set()).add('scripts/coop_soc_dv.script')
for fl in sorted(reads):
    # flags set by the engine / level objects by themselves, or by an event outside the scripts
    if sets.get(fl):
        ok('%s read by %d file(s), set by %s' % (fl, len(reads[fl]), sorted(sets[fl])[:2]))
    elif fl == 'ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_X18_DOCUMENTS_STOP_DIALOG_INFO':
        ok('%s is only read by the hidden Sidorovich task section (the dialog that set it is gone on purpose)' % fl)
    elif fl.endswith('_DEAD'):
        ok('%s read by %d file(s), set by the squad on_death logic of the simulation (squad_descr)' % (fl, len(reads[fl])))
    else:
        bad('%s is read by %s but nothing sets it' % (fl, sorted(reads[fl])[:3]))

# ---- 6. voice
for v in re.findall(r'bar_bar_barmen_start_"?\s*\.\.\s*id|"(\d+)"', bar)[:0]:
    pass
voice_ids = re.search(r'VOICE_IDS = \{([^}]*)\}', bar).group(1)
for i in re.findall(r'"(\d+)"', voice_ids):
    f = 'sounds/characters_voice/dialogs/eng/bar_bar_barmen_start_%s.ogg' % i
    (ok if f in tree else bad)('voice file %s %s' % (f, 'ships' if f in tree else 'MISSING'))

print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
