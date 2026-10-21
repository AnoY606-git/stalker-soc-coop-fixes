"""Static check of the Cordon story chain after the flash drive (patch cordon). Offline, seconds.
  python patches\\cordon\\tools\\check_cordon_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b]

Builds the EFFECTIVE tree (the mod source, every patch of patches\\ copied over it in sorted order like build.py, minus --skip) and proves:
  1. the new dialogs: every Lua function exists in coop_soc_cordon.script, every text id exists in eng and rus, every flag exists in story_flags_table
  2. every task id given in the effective Cordon logic / dialogs / task files has a section, or is in coop_hidden_tasks.ltx; every title / descr id exists (eng + rus);
     every task the server tick gives exists
  3. the helicopter flight and its task are gone (no heli_move@fly sections, no give_task of the helicopter task), also the radio flyover
     of esc_smart_terrain_5_helicopter (before the hand-in)
  4. every flag that a later level (everything that is not Cordon) reads from the Cordon story is still set by something in the effective tree
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

# ---- effective tree: relpath (lower, forward slashes) -> (owner, path)
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


# ---- story flags
flags = set()
for m in re.finditer(r'\["([A-Za-z0-9_]+)"\]\s*=\s*\d+', read('scripts/story_flags_table.script')):
    flags.add(m.group(1).upper())

# flags that are not in the table are fine (the engine syncs them by name, packet id 65535); a flag in a NEW dialog must at least be used somewhere else in the mod
used_flags = set()
for db in ('gamedata.db0', 'gamedata.db1'):
    for dp, _, fs in os.walk(os.path.join(mod, db)):
        for f in fs:
            if f.endswith(('.ltx', '.xml', '.script', '.dscript')) and 'text' not in os.path.relpath(dp, mod).lower().split(os.sep):
                raw = open(os.path.join(dp, f), 'rb').read().decode('utf-8', errors='replace')
                used_flags.update(m.upper() for m in re.findall(r'([A-Za-z][A-Za-z0-9_]*_(?:INFO|DEAD))', raw, re.I))

# ---- text ids per language (all st_*.xml of the effective tree)
text = {'eng': set(), 'rus': set()}
for rel in tree:
    m = re.match(r'configs/text/(eng|rus)/[^/]+\.xml$', rel)
    if m:
        for sm in re.finditer(r'<string id="([^"]*)"', read(rel)):
            text[m.group(1)].add(sm.group(1))

# ---- 1. new dialogs
dlg = read('configs/gameplay/dialogs_coop_l01_escape.xml')
scr = read('scripts/coop_soc_cordon.script')
fns = set(re.findall(r'^function\s+(\w+)', scr, re.M))
for fn in set(re.findall(r'coop_soc_cordon\.(\w+)', dlg)):
    (ok if fn in fns else bad)('dialog function coop_soc_cordon.%s %s' % (fn, 'defined' if fn in fns else 'MISSING'))
for tid in sorted(set(re.findall(r'<text>(coop_soc_\w+)</text>', dlg))):
    for lang in ('eng', 'rus'):
        if tid not in text[lang]:
            bad('text %s missing in %s' % (tid, lang))
for fl in sorted(set(re.findall(r'<(?:give_flag|has_flag|dont_has_flag|disable_flag)>\s*(\S+?)\s*</', dlg))):
    if fl.upper() not in flags and fl.upper() not in used_flags and not fl.upper().startswith(('COOP_SOC_',)):
        bad('flag %s is neither in story_flags_table nor used anywhere in the mod' % fl)
ok('dialog flags, functions and texts checked (%d flags known)' % len(flags))
for d in ('esc_smart_terrain_7_military_kuznetsov_go_to_fox_2',):
    if d in dlg:
        bad('dialog %s still in the xml' % d)
if 'go_to_fox_2' in read('configs/gameplay/character_desc_coop_l01_escape.xml').replace('<!-- vodka pass dialog (go_to_fox_2)', ''):
    bad('Kuznetsov still offers go_to_fox_2')
if re.search(r'transfer_vodka|if_actor_has_vodka|<text>[^<]*vodka', dlg, re.I):
    bad('the Cordon dialogs still use vodka')

# ---- 2. tasks
tm_text = ''
for rel in tree:
    if re.match(r'configs/misc/tm_coop_.*\.ltx$', rel):
        tm_text += read(rel) + '\n'
sections = {}
cur = None
for line in tm_text.splitlines():
    line = line.strip()
    m = re.match(r'\[([^\]]+)\]', line)
    if m:
        cur = m.group(1)
        sections[cur] = {}
    elif cur and '=' in line and not line.startswith(';'):
        k, v = [x.strip() for x in line.split('=', 1)]
        sections[cur][k] = v
hidden = set(l.strip() for l in read('configs/misc/coop_hidden_tasks.ltx').splitlines() if l.strip() and not l.startswith(';') and not l.startswith('['))
cordon_logic = [rel for rel in tree if 'coop_l01_escape' in rel and rel.endswith(('.ltx', '.xml')) and not rel.startswith('configs/text')]
cordon_logic += ['configs/misc/tm_coop_l01_escape.ltx', 'configs/gameplay/dialogs_coop_l01_escape.xml']
given = {}
for rel in sorted(set(cordon_logic)):
    for m in re.finditer(r'give_task\((\w+)', read(rel)):
        given.setdefault(m.group(1), set()).add(rel)
for tid, rels in sorted(given.items()):
    if tid in hidden:
        continue
    if tid not in sections:
        bad('give_task(%s) in %s has no section' % (tid, sorted(rels)[0]))
tick = set(re.findall(r'\{ id = "(\w+)"', read('scripts/coop_soc_opening.script')))
for tid in sorted(tick):
    if tid not in sections:
        bad('server tick gives %s: no section' % tid)
    if tid in hidden and tid != 'esc_start_main_quest_task':
        bad('server tick gives %s but it is hidden' % tid)
for tid in ('esc_soc_trader_job_task', 'esc_soc_railroad_passage_task', 'esc_soc_military_documents_task'):
    sec = sections.get(tid)
    if not sec:
        bad('task section %s missing' % tid)
        continue
    for k in ('title', 'descr'):
        # a value may be a condlist (patch agroprom_soc: "{+FLAG} id, {+FLAG2} id2, id3"): every id of it must exist
        ids = [re.sub(r'\{[^}]*\}', '', part).strip() for part in re.split(r',(?![^{]*\})', sec[k])]
        for lang in ('eng', 'rus'):
            for sid in ids:
                if sid not in text[lang]:
                    bad('%s %s=%s missing in %s' % (tid, k, sid, lang))
sec = sections['esc_start_5_bottles_of_vodka_for_kuznetsov_quest_task']
for k in ('title', 'descr'):
    for lang in ('eng', 'rus'):
        if sec[k] not in text[lang]:
            bad('bridge pass task %s=%s missing in %s' % (k, sec[k], lang))
ok('tasks: %d given ids resolved, %d hidden, tick tasks %s' % (len(given), len(hidden), sorted(tick)))
for tid in ('esc_start_talk_to_the_sidorovich_quest_1_task', 'esc_start_talk_to_the_fox_quest_1_task', 'esc_start_talk_to_the_fox_quest_2_task'):
    (ok if tid in hidden else bad)('removed task %s %s' % (tid, 'is hidden' if tid in hidden else 'NOT hidden'))

# ---- 3. helicopter flight
for n in (1, 2, 3):
    rel = 'configs/scripts/coop_l01_escape/esc_helicopter_go_to_agroprom_%d.ltx' % n
    t = read(rel)
    if 'heli_move@fly' in t or 'give_task' in t or 'path_move = esc_helicopter_go_to_agroprom_%d_move_way' % n in t:
        bad('%s still flies / gives a task' % rel)
    elif 'destroy_object' not in t:
        bad('%s does not remove the helicopter' % rel)
    else:
        ok('%s: no flight, no task (owner %s)' % (rel, tree[rel][0]))
rel = 'configs/scripts/coop_l01_escape/esc_smart_terrain_5_helicopter.ltx'   # the radio flyover before the hand-in (SoC has none)
t = read(rel)
if 'heli_move@fly' in t or 'give_task' in t or 'play_sound' in t or 'esc_helicopter_move_way' in t:
    bad('%s still flies / plays the radio sound' % rel)
elif 'destroy_object' not in t:
    bad('%s does not remove the helicopter' % rel)
else:
    ok('%s: no flyover, no sound (owner %s)' % (rel, tree[rel][0]))
cs = read('scripts/coop_soc_cordon.script')
(ok if 'esc_smart_terrain_5_helicopter' in cs and 'pcall(release_helis, true)' in cs else bad)('coop_soc_cordon releases the flyover object on the server')
sr = read('configs/scripts/coop_l01_escape/space_restrictors/esc_start_main_quest_task_space_restrictor.ltx')
(bad if re.search(r'HELICOPTER|VODKA|KUZNETSOV|give_task\(esc_start_talk_to_the_sidorovich_quest_1', sr) else ok)('start restrictor has no helicopter / vodka step')

# ---- 4. flags later levels read from the Cordon story
ESC = re.compile(r'\b(ESC_[A-Z0-9_]+)\b')
# producers: anything that gives / sets a flag: give_flag, %+FLAG%, +FLAG inside %..%, GiveFlag in scripts
reads = {}
sets = {}
for rel in tree:
    if not rel.endswith(('.ltx', '.xml', '.script', '.dscript')):
        continue
    if rel.startswith(('configs/text/', 'configs/ui/')) or rel in ('scripts/story_flags_table.script', 'scripts/coop_quest_dialogs.script'):
        continue
    t = read(rel)
    cordon = 'coop_l01_escape' in rel or rel in ('configs/misc/tm_coop_l01_escape.ltx', 'scripts/coop_soc_opening.script', 'scripts/coop_scn_opening.script') \
        or rel.startswith('scripts/coop_soc_cordon')
    for m in ESC.finditer(t):
        fl = m.group(1)
        if fl not in flags:
            continue
        # a flag is "set" when it is inside %...% of an ltx line or in give_flag
        line = t[t.rfind('\n', 0, m.start()) + 1:t.find('\n', m.end())]
        in_pct = False
        if rel.endswith('.ltx'):
            for pm in re.finditer(r'%([^%]*)%', line):
                if m.start() - (t.rfind('\n', 0, m.start()) + 1) >= pm.start() and fl in pm.group(1):
                    in_pct = True
        set_here = ('<give_flag>' + fl in t[m.start() - 12:m.end()]) or in_pct or ('give_flag("%s")' % fl in t[m.start() - 12:m.end() + 3])
        if set_here:
            sets.setdefault(fl, set()).add(rel)
        elif not cordon:
            reads.setdefault(fl, set()).add(rel)
if not reads:
    ok('no later level reads an ESC_ flag from the Cordon story')
for fl, rels in sorted(reads.items()):
    prod = sets.get(fl, set())
    if fl.startswith('ESC_TEST_'):
        continue                      # the level maker's own test flags, never set before either
    msg = '%s read by %s, set by %s' % (fl, sorted(rels)[:3], sorted(prod)[:3])
    (ok if prod else bad)(msg)

# flags the removed steps used to set, and who sets them now
for fl, why in (('ESC_HELICOPTER_GO_TO_AGROPROM_INFO', 'was set by the helicopter, now silently by the flash drive hand-in dialog'),
                ('ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO', 'was set by the go_to_fox talk, now by the SoC military case talk'),
                ('ESC_START_5_BOTTLES_OF_VODKA_FOR_KUZNETSOV_QUEST_TASK_INFO', 'bridge pass, now set by paying 500 rubles'),
                ('ESC_SMART_TERRAIN_7_MILITARY_KUZNETSOV_GO_TO_FOX_1_STOP_DIALOG_INFO', 'kept for old logic, set by the 500 rubles phrase'),
                ('ESC_SMART_TERRAIN_7_MILITARY_KUZNETSOV_GO_TO_FOX_2_STOP_DIALOG_INFO', 'kept for old logic, set by the 500 rubles phrase')):
    (ok if re.search(r'<give_flag>\s*%s\s*</give_flag>' % fl, dlg) else bad)('%s: %s' % (fl, why))
print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
