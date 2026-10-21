"""Static check of the Garbage quest chain (patch garbage_soc_quests). Offline, seconds.
  python patches\\garbage_soc_quests\\tools\\check_garbage_chain.py <mod source dir (has gamedata.db0, gamedata.db1)> [--skip=a,b]

Builds the EFFECTIVE tree (the mod source, every patch of patches\\ copied over it in sorted order like build.py, minus --skip) and proves:
  1. every task the server tick of coop_scn_garbage_soc.script gives has a section in an effective tm_coop file, title / descr ids (also inside condlists) exist
     in eng and rus, and none of them is hidden; the level maker's "help the Gray" task is hidden and not given by any logic file of the Garbage
  2. dialogs_coop_l02_garbage.xml: valid XML, every <next> resolves, every <text> id exists (eng + rus), every module.function of an action / precondition exists
     in the scripts of the effective tree, every flag in a dialog is known (story_flags_table, the mod's own flags, or a flag this patch's script gives)
  3. character_desc: every start_dialog / actor_dialog of Seriy, Bes and the commander exists
  4. logic files: every walker@/kamp@/meet@ target an on_info line of Seriy, Bes and the commander names exists in the same file; Seriy and Bes wait for the arrival flag, not for the
     Yurik / Bes steps; the commander's walker is not no_meet
  5. flag report: every flag this patch reads or gives, who else reads / sets it (all levels, all patches)
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


def condlist_ids(v):
    return [re.sub(r'\{[^}]*\}', '', part).strip() for part in re.split(r',(?![^{]*\})', v)]


flags = set()
for m in re.finditer(r'\["([A-Za-z0-9_]+)"\]\s*=\s*\d+', read('scripts/story_flags_table.script')):
    flags.add(m.group(1).upper())

text = {'eng': set(), 'rus': set()}
for rel in tree:
    m = re.match(r'configs/text/(eng|rus)/[^/]+\.xml$', rel)
    if m:
        for sm in re.finditer(r'<string id="([^"]*)"', read(rel)):
            text[m.group(1)].add(sm.group(1))

script = read('scripts/coop_scn_garbage_soc.script')
duty_script = read('scripts/coop_scn_garbage_duty.script')
own_flags = set(re.findall(r'"((?:GAR|ESC|AGR)_[A-Z0-9_]+|GAR_SOC_[A-Z0-9_]+)"', script))
own_flags |= set(re.findall(r'"(GAR_[A-Z0-9_]+)"', duty_script))

# ---- tasks
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
tick = re.findall(r'\{ id = "(\w+)"', script)
for tid in tick:
    sec = sections.get(tid)
    if not sec:
        bad('server tick gives %s: no section' % tid)
        continue
    if tid in hidden:
        bad('server tick gives %s but it is hidden' % tid)
    for k in ('title', 'descr'):
        for lang in ('eng', 'rus'):
            for sid in condlist_ids(sec.get(k, '')):
                if sid not in text[lang]:
                    bad('%s %s=%s missing in %s' % (tid, k, sid, lang))
    for k in ('condlist_0', 'condlist_1'):
        for m in re.finditer(r'give_task\((\w+)', sec.get(k, '')):
            if m.group(1) not in sections:
                bad('%s %s gives %s: no section' % (tid, k, m.group(1)))
ok('tick tasks (%d) have a section, title and descr in eng + rus: %s' % (len(tick), ', '.join(tick)))
A = 'gar_start_help_the_gray_to_fight_off_the_bandits_quest_task'
(ok if A in hidden else bad)('level maker task %s is %s' % (A, 'hidden' if A in hidden else 'NOT hidden'))
for rel in sorted(tree):
    if 'coop_l02_garbage' in rel and rel.endswith(('.ltx', '.xml')) and not rel.startswith('configs/text') and not rel.startswith('levels'):
        t = read(rel)
        for m in re.finditer(r'give_task\(' + A, t):
            ok('give_task(%s) in %s stays in a state that is never reached any more (hidden task, old saves only)' % (A[:24] + '...', rel))
if 'reward_money' in sections['gar_start_help_fight_off_the_mutants_quest_task']:
    bad('the kill task still pays the boar reward (the commander dialog pays it now)')
else:
    ok('boar reward moved from the task to the commander dialog (%d RU)' % 1500)
for tid in ('gar_start_talk_to_gray_quest_task', 'gar_start_talk_to_devil_1_quest_task'):
    (bad if 'reward_money' in sections[tid] else ok)('%s pays no tm reward (SoC pays in the dialog)' % tid)
for did, fn in (('gar_smart_terrain_2_stalker_gray_help', 'pay_seriy'), ('gar_smart_terrain_2_stalker_gray_help_nofox', 'pay_seriy'), ('gar_smart_terrain_4_stalker_devil_help_the_and', 'pay_bes')):
    m = re.search(r'<dialog id="%s">.*?</dialog>' % did, read('configs/gameplay/dialogs_coop_l02_garbage.xml'), re.S)
    (ok if m and 'coop_scn_garbage_soc.' + fn in m.group(0) else bad)('dialog %s pays through %s' % (did, fn))
k2 = sections['gar_soc_duty_report_task']
(ok if 'GAR_SOC_DUTY_REPORT_INFO' in k2['condlist_0'] else bad)('commander task completes with the report flag')
g = sections['gar_start_talk_to_gray_quest_task']
(ok if 'st_gar_start_help_the_gray_to_fight_off_the_bandits_quest_task_descr' in g['descr'] and '{+GAR_WAITING' in g['target'] else bad)('Seriy task: briefing text before the arrival, objective text and marker after it')

# ---- dialogs
dlg_rel = 'configs/gameplay/dialogs_coop_l02_garbage.xml'
dlg = read(dlg_rel)
try:
    dom = xml.dom.minidom.parseString(open(tree[dlg_rel][1], 'rb').read())
    ok('dialogs xml is well formed (owner %s)' % tree[dlg_rel][0])
except Exception as e:
    bad('dialogs xml: %s' % e)
    dom = None
fns = {}
for rel in tree:
    if rel.startswith('scripts/') and rel.endswith(('.script', '.dscript')):
        mod_name = os.path.basename(rel).split('.')[0]
        fns.setdefault(mod_name, set()).update(re.findall(r'^function\s+(\w+)', read(rel), re.M))
base_scripts = os.path.join(os.path.dirname(os.path.normpath(mod)), 'source_base', 'xrmpe_patch', 'scripts')
if os.path.isdir(base_scripts):
    for f in os.listdir(base_scripts):
        if f.endswith(('.script', '.dscript')):
            fns.setdefault(f.split('.')[0], set()).update(re.findall(r'^function\s+(\w+)', open(os.path.join(base_scripts, f), 'rb').read().decode('latin-1'), re.M))
TOUCHED = ('gar_smart_terrain_2_stalker_gray_start_dialog', 'gar_smart_terrain_2_stalker_gray_help', 'gar_smart_terrain_2_stalker_gray_help_nofox', 'gar_smart_terrain_4_stalker_devil_help_the_and', 'gar_duty_pass_start_dialog')
ndlg = 0
if dom is not None:
    for d in dom.getElementsByTagName('dialog'):
        ndlg += 1
        did = d.getAttribute('id')
        ids = set(p.getAttribute('id') for p in d.getElementsByTagName('phrase'))
        for p in d.getElementsByTagName('phrase'):
            for n in p.getElementsByTagName('next'):
                v = ''.join(c.data for c in n.childNodes if c.nodeType == c.TEXT_NODE).strip()
                if v not in ids:
                    bad('dialog %s phrase %s: next %s does not exist' % (did, p.getAttribute('id'), v))
            for t in p.getElementsByTagName('text'):
                v = ''.join(c.data for c in t.childNodes if c.nodeType == c.TEXT_NODE).strip()
                if v:
                    for lang in ('eng', 'rus'):
                        if v not in text[lang]:
                            bad('dialog %s: text %s missing in %s' % (did, v, lang))
            for tag in (('action', 'precondition') if did in TOUCHED else ()):
                for n in p.getElementsByTagName(tag):
                    v = ''.join(c.data for c in n.childNodes if c.nodeType == c.TEXT_NODE).strip()
                    mm = re.match(r'(\w+)\.(\w+)$', v)
                    if not mm or mm.group(2) not in fns.get(mm.group(1), set()):
                        bad('dialog %s: %s %s is not defined in any script' % (did, tag, v))
        for tag in (('has_flag', 'dont_has_flag', 'give_flag', 'disable_flag') if did in TOUCHED else ()):
            for n in d.getElementsByTagName(tag):
                v = ''.join(c.data for c in n.childNodes if c.nodeType == c.TEXT_NODE).strip().upper()
                if v not in flags and v not in own_flags:
                    bad('dialog %s: flag %s is not in story_flags_table and not given by this chain' % (did, v))
ok('%d dialogs: next ids, texts (eng + rus), functions and flags resolved' % ndlg)

# ---- character_desc
cd = read('configs/gameplay/character_desc_coop_l02_garbage.xml')
dids = set(re.findall(r'<dialog id="([^"]+)"', dlg))
for who in ('gar_smart_terrain_2_stalker_gray', 'gar_smart_terrain_4_stalker_devil', 'gar_smart_terrain_8_duty_prapor'):
    m = re.search(r'<specific_character id="%s".*?</specific_character>' % who, cd, re.S)
    if not m:
        bad('character %s missing' % who)
        continue
    used = re.findall(r'<(?:start_dialog|actor_dialog)>([^<]+)</', m.group(0))
    for u in used:
        if u.strip() not in dids:
            bad('%s uses dialog %s: not in the dialog file' % (who, u))
    ok('%s: dialogs %s' % (who, ', '.join(u.strip() for u in used)))

# ---- logic files
def ltx_sections(t):
    return set(m.group(1) for m in re.finditer(r'^\[([^\]]+)\]', t, re.M))


for rel, expect in (('configs/scripts/coop_l02_garbage/gar_smart_terrain_7_walker_gray.ltx', 'GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO'),
                    ('configs/scripts/coop_l02_garbage/gar_smart_terrain_2_walker_devil.ltx', 'GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO'),
                    ('configs/scripts/coop_l02_garbage/gar_smart_terrain_9_walker_prapor.ltx', None)):
    t = read(rel)
    secs = ltx_sections(t)
    refs = set()
    for m in re.finditer(r'^\s*(?:on_\w+|meet|active)\s*=\s*([^;\r\n]*)', t, re.M):
        for mm in re.finditer(r'\b((?:walker|kamp|meet|animpoint)@[\w@]+)', m.group(1)):
            refs.add(mm.group(1))
    for r in sorted(refs):
        if r not in secs:
            bad('%s: %s is referenced but there is no such section' % (rel, r))
    if expect:
        init = t.split('\n[', 2)[1] if t.count('\n[') >= 1 else t
        first = re.search(r'^on_info\s*=.*$', t, re.M).group(0)
        (ok if expect in first and 'DEVIL_HELP_THE_AND' not in first and 'YURIK_SQUAD_DEAD' not in first else bad)('%s: first on_info waits for the arrival: %s' % (os.path.basename(rel), first[:100]))
    else:
        w = re.search(r'\[walker@gar_smart_terrain_9_walker_prapor\](.*?)(?=\n\[)', t, re.S).group(1)
        (bad if re.search(r'^meet\s*=\s*no_meet', w, re.M) else ok)('commander walker is not no_meet (talk allowed)')
        (ok if re.search(r'\[meet@gar_smart_terrain_9_prapor\][^\[]*use\s*=\s*\{=actor_enemy\} false, true', t) else bad)('commander meet section has a normal use rule')
    ok('%s: %d sections, %d references resolved (owner %s)' % (os.path.basename(rel), len(secs), len(refs), tree[rel][0]))

fmap = dict(re.findall(r'^	(\w+)\s*=\s*"([A-Z0-9_]+)"', script, re.M))
script_gives = set(fmap[k] for k in re.findall(r'give\(F\.(\w+)\)', script) if k in fmap)
duty_gives = set(re.findall(r'give_flag\((?:PASS_FLAG|GRAY_FLAG)\)', duty_script)) and {'GAR_FREE_PASS', 'GAR_THE_ORDER_TO_KILL_GRAY_INFO'}

# ---- flag report (informational, plus: every flag the script reads is set by something)
set_by = {}
read_by = {}
for rel in tree:
    if not rel.endswith(('.ltx', '.xml', '.script', '.dscript', '.lua')) or rel.startswith(('configs/text/', 'configs/ui/')) or rel == 'scripts/story_flags_table.script':
        continue
    t = read(rel)
    for fl in own_flags:
        for m in re.finditer(r'\b' + re.escape(fl) + r'\b', t):
            ctx = t[max(0, m.start() - 24):m.end() + 2]
            line = t[t.rfind('\n', 0, m.start()) + 1:t.find('\n', m.end())]
            is_set = ('<give_flag>' + fl) in ctx or ('give("' in ctx) or ('give_flag' in ctx) or \
                (rel.endswith('.ltx') and re.search(r'%[^%]*\+' + re.escape(fl), line) is not None)
            (set_by if is_set else read_by).setdefault(fl, set()).add(rel)
for fl in script_gives | duty_gives:
    set_by.setdefault(fl, set()).add('scripts/coop_scn_garbage_soc.script' if fl in script_gives else 'scripts/coop_scn_garbage_duty.script')
for fl in sorted(own_flags):
    s, r = sorted(set_by.get(fl, [])), sorted(read_by.get(fl, []))
    print('flag   %-72s set by %d (%s) read by %d (%s)' % (fl, len(s), ', '.join(os.path.basename(x) for x in s[:3]), len(r), ', '.join(os.path.basename(x) for x in r[:3])))
for fl in ('GAR_SOC_DUTY_REPORT_INFO', 'GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO', 'GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO',
           'GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO', 'GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO'):
    (ok if set_by.get(fl) else bad)('%s is set by %s' % (fl, ', '.join(os.path.basename(x) for x in sorted(set_by.get(fl, []))[:4]) or 'NOTHING'))

print('%d problem(s)' % len(problems))
sys.exit(1 if problems else 0)
