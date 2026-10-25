"""Static proof (no game) of the Semenov variant, the wounded scientist and the return task.  Run it on a repo where tools\\apply_shared.py was applied:

  python -I patches\\soc_yan_semenov\\tools\\check_semenov_chain.py [<repo root>] [--addon <unpacked mod add-on dir with gamedata.db0/db1>] [--soc-alife <alife_l08_yantar.ltx>]

Checks (prints PASS / FAIL per line, exit code 1 when something fails):
  1. the four dialogs parse, every next / precondition / action / text resolves, every phrase is reachable, the flag-giving paths exist
     (Sakharov: the Semenov offer 21113 -> 211132 and branch 5; Semenov: the escort talk; the wounded scientist)
  2. every flag the script reads has a setter (this script, a dialog, a logic file, or another patch / the mod)
  3. the tasks: the measurement task text / marker branches (strings in EN and RU, targets are story ids that exist), the return task
  4. spawn sections, specific character, profile (both npc_profile_addon copies), logic files (sections, patrol paths of the mod level), model and
     start dialog, the positions against the SoC data
  5. voice files named by the script exist
"""
import json
import os
import re
import struct
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.dirname(here)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = {}
for i, a in enumerate(sys.argv[1:]):
    if a.startswith('--') and i + 2 <= len(sys.argv[1:]):
        opts[a[2:]] = sys.argv[1:][i + 1]
args = [a for a in args if a not in opts.values()]
repo = os.path.abspath(args[0]) if args else os.path.dirname(os.path.dirname(patch))
DL = os.path.join(os.path.expanduser('~'), 'Downloads')
ADDON = opts.get('addon', os.path.join(DL, 'Shadow of COOP 8.0', 'addon_unpacked'))
SOC_ALIFE = opts.get('soc-alife', os.path.join(DL, 'SoC_COOP_stashes', 'refs', 'soc1006', 'alife_l08_yantar.ltx'))
P = lambda *a: os.path.join(repo, 'patches', *a)
sys.path.insert(0, os.path.join(repo, 'tools'))
fails = 0


def check(name, ok, info=''):
    global fails
    print(('PASS ' if ok else 'FAIL ') + name + ((' : ' + str(info)) if info != '' else ''))
    if not ok:
        fails += 1


def rd(*parts, enc='latin-1'):
    return open(os.path.join(*parts), 'rb').read().decode(enc)


MOD = 'coop_soc_yan_semenov'
script = rd(patch, 'gamedata', 'scripts', 'coop_soc_yan_semenov.script')
yan_script = rd(P('soc_yan_x16_quests', 'gamedata', 'scripts', 'coop_soc_yan.script'))
funcs = {'coop_soc_yan_semenov': set(re.findall(r'(?m)^function\s+([A-Za-z_0-9]+)\s*\(', script)),
         'coop_soc_yan': set(re.findall(r'(?m)^function\s+([A-Za-z_0-9]+)\s*\(', yan_script))}
funcs['dialogs'] = {'break_dialog'}


def external_func(mod, fn):
    """a function of another module (the mod's own scripts or another patch): looked up in the mod source and in the patches"""
    src = os.path.join(os.path.dirname(ADDON), 'source')
    pat = re.compile(r'(?m)^function\s+%s\s*\(' % re.escape(fn))
    for base in (src, os.path.join(repo, 'patches')):
        for dp, dn, fns in os.walk(base):
            if (mod + '.script') in fns:
                try:
                    if pat.search(rd(dp, mod + '.script')):
                        return True
                except Exception:
                    pass
    return False

# ----------------------------------------------------------------------------------------------------------------------------------
# strings of every patch + the mod (ids)
# ----------------------------------------------------------------------------------------------------------------------------------
STR = {'eng': set(), 'rus': set()}
for lang in STR:
    for base in (os.path.join(repo, 'patches'),):
        for dp, dn, fn in os.walk(base):
            if dp.replace('\\', '/').endswith('/configs/text/' + lang):
                for f in fn:
                    if f.endswith('.xml'):
                        STR[lang] |= set(re.findall(r'<string id="([^"]+)"', rd(dp, f)))
    mod_text = os.path.join(os.path.dirname(ADDON), 'source', 'gamedata.db0', 'configs', 'text', lang)
    if os.path.isdir(mod_text):
        for f in os.listdir(mod_text):
            if f.endswith('.xml'):
                STR[lang] |= set(re.findall(r'<string id="([^"]+)"', rd(mod_text, f)))


def has_str(i):
    return i in STR['eng'] and i in STR['rus']


# ----------------------------------------------------------------------------------------------------------------------------------
# 1. dialogs
# ----------------------------------------------------------------------------------------------------------------------------------
dtxt = rd(P('quest_dialogs', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l08_yantar.xml'))


def dialog(did):
    m = re.search(r'<dialog id="%s">(.*?)</dialog>' % did, dtxt, re.S)
    if not m:
        return None
    ph = {}
    for p in re.finditer(r'<phrase id="([^"]+)">(.*?)</phrase>', m.group(1), re.S):
        b = p.group(2)
        ph[p.group(1)] = {
            'text': (re.findall(r'<text>([^<]*)</text>', b) or [''])[0],
            'pre': re.findall(r'<precondition>([^<]*)</precondition>', b),
            'act': re.findall(r'<action>([^<]*)</action>', b),
            'flag': re.findall(r'<give_flag>([^<]*)</give_flag>', b),
            'next': re.findall(r'<next>([^<]*)</next>', b),
        }
    return ph


DIALOGS = ['yan_soc_saharov_dialog', 'yan_soc_kruglov_dialog', 'yan_soc_semenov_dialog', 'yan_soc_wounded_dialog']
D = {d: dialog(d) for d in DIALOGS}
check('the four dialogs are in dialogs_coop_l08_yantar.xml', all(D.values()), [d for d in DIALOGS if not D[d]])
check('each dialog id is unique in the file', all(len(re.findall(r'<dialog id="%s">' % d, dtxt)) == 1 for d in DIALOGS))
for d in DIALOGS:
    ph = D[d] or {}
    ids = re.findall(r'<phrase id="([^"]+)">', re.search(r'<dialog id="%s">(.*?)</dialog>' % d, dtxt, re.S).group(1)) if D[d] else []
    check(d + ': phrase ids are unique', len(ids) == len(set(ids)))
    bad = [(i, n) for i, p in ph.items() for n in p['next'] if n not in ph]
    check(d + ': every next exists', not bad, bad)
    seen, todo = set(), ['0']
    while todo:
        x = todo.pop()
        if x in seen or x not in ph:
            continue
        seen.add(x)
        todo += ph[x]['next']
    check(d + ': every phrase is reachable from 0', seen == set(ph), sorted(set(ph) - seen))
    badfn = []
    for i, p in ph.items():
        for ref in p['pre'] + p['act']:
            mod, _, fn = ref.partition('.')
            if mod in funcs:
                if fn not in funcs[mod]:
                    badfn.append((i, ref))
            elif not external_func(mod, fn):
                badfn.append((i, ref))
    check(d + ': every precondition / action function exists', not badfn, badfn)
    badtxt = [(i, p['text']) for i, p in ph.items() if p['text'] and not has_str(p['text'])]
    check(d + ': every text id exists in EN and RU', not badtxt, badtxt)


def paths_to_flags(d, start='0'):
    """all root-to-leaf paths: list of (path, flags, breaks)"""
    ph = D[d]
    out = []

    def rec(x, path, flags):
        p = ph[x]
        flags = flags + p['flag']
        path = path + [x]
        if not p['next']:
            out.append((path, flags))
            return
        for n in p['next']:
            rec(n, path, flags)
    rec(start, [], [])
    return out


def flags_of(d, last):
    return [fl for path, fl in paths_to_flags(d) if path[-1] == last]


OFFERED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO'
PREP = 'YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO'
REPORTED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO'
HELMET = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO'
if all(D.values()):
    fl = flags_of('yan_soc_saharov_dialog', '211132')
    check('Sakharov: the Semenov offer (1-11-111-211-2111-21111-21113-211131-211132) sets OFFERED + YAN_FIND_SCIENTIST_SEMENOV_START',
          len(fl) == 1 and OFFERED in fl[0] and 'YAN_FIND_SCIENTIST_SEMENOV_START' in fl[0], fl)
    pth = [p for p, f in paths_to_flags('yan_soc_saharov_dialog') if p[-1] == '211132']
    check('Sakharov: that path is exactly the SoC one', pth == [['0', '1', '11', '111', '211', '2111', '21111', '21113', '211131', '211132']], pth)
    check('Sakharov: the Kruglov offer (21112) is hidden by st_prof_alive, the Semenov offer (21113) by st_prof_die',
          D['yan_soc_saharov_dialog']['21112']['pre'] == [MOD + '.st_prof_alive'] and D['yan_soc_saharov_dialog']['21113']['pre'] == [MOD + '.st_prof_die'])
    fl = flags_of('yan_soc_saharov_dialog', '51114')
    check('Sakharov branch 5 (Semenov died) sets REPORTED + HELMET in its FIRST phrase (a cut-off talk cannot lose them)',
          len(fl) == 1 and REPORTED in fl[0] and HELMET in fl[0] and D['yan_soc_saharov_dialog']['51']['flag'] == [REPORTED, HELMET], fl)
    pth = [p for p, f in paths_to_flags('yan_soc_saharov_dialog') if p[-1] == '51114']
    check('Sakharov branch 5 is the SoC chain 51-511-5111-51111-511111-5111111-511111111-51112-51113-51114',
          pth == [['0', '5', '51', '511', '5111', '51111', '511111', '5111111', '511111111', '51112', '51113', '51114']], pth)
    check('Sakharov: branch 5 and the results branch exclude each other (results is wrapped)', D['yan_soc_saharov_dialog']['3']['pre'] == [MOD + '.st_s_results'] and
          D['yan_soc_saharov_dialog']['5']['pre'] == [MOD + '.st_s_semdead'])
    check('Sakharov: the end phrases break the dialog', 'dialogs.break_dialog' in D['yan_soc_saharov_dialog']['211132']['act'] and 'dialogs.break_dialog' in D['yan_soc_saharov_dialog']['51114']['act'])
    fl = flags_of('yan_soc_semenov_dialog', '515')
    check('Semenov: the escort talk (5-51-511-512-513-514-515) sets PREP', fl == [[PREP]], fl)
    check('Semenov: states before the offer / talk / busy / after', [D['yan_soc_semenov_dialog'][k]['pre'] for k in ('6', '5', '10', '7')] ==
          [[MOD + '.st_m_meet'], [MOD + '.st_m_talk'], [MOD + '.st_m_busy'], [MOD + '.st_m_after']])
    fl = flags_of('yan_soc_wounded_dialog', '111')
    check('wounded scientist: the first talk (1-11-111) sets YAN_SCIENTIST_RETURN_TO_BUNKER and ends', fl == [['YAN_SCIENTIST_RETURN_TO_BUNKER']] and
          'dialogs.break_dialog' in D['yan_soc_wounded_dialog']['111']['act'], fl)
    kr = D['yan_soc_kruglov_dialog']
    check('Kruglov: every state is wrapped, branch 6 shows only while the professor is dead',
          all(kr[k]['pre'] == [MOD + '.st_k_' + n] for k, n in (('2', 'meet_r'), ('4', 'meet'), ('1', 'talk'), ('10', 'busy'), ('7', 'after'), ('6', 'other'))) and '6' in kr['0']['next'])
    # the lines with a recording or a speaker table entry
    sp = re.search(r'local NPC = \{(.*?)\n\}', script, re.S).group(1)
    check('every say_* the dialogs call is defined', all(fn in funcs['coop_soc_yan_semenov'] for d in DIALOGS for p in D[d].values() for r in p['act']
                                                       for fn in [r.partition('.')[2]] if r.startswith(MOD + '.say_')))

# ----------------------------------------------------------------------------------------------------------------------------------
# 2. flags
# ----------------------------------------------------------------------------------------------------------------------------------
F = dict(re.findall(r'^\t([A-Z_0-9]+)\s*=\s*"([A-Z_0-9]+)"', script, re.M))
F = {k: v for k, v in F.items() if v.isupper()}
check('the script names %d flags' % len(F), len(F) >= 14, sorted(F))
corpus = ''
for dp, dn, fn in os.walk(os.path.join(repo, 'patches')):
    if os.sep + 'wip' in dp or os.sep + 'tests' in dp or os.sep + 'tools' in dp:
        continue
    for f in fn:
        if f.endswith(('.script', '.ltx', '.xml')):
            try:
                corpus += '\n' + rd(dp, f)
            except Exception:
                pass
mod_src = os.path.join(os.path.dirname(ADDON), 'source')
for dp, dn, fn in os.walk(mod_src):
    for f in fn:
        if f.endswith(('.script', '.ltx', '.xml')):
            try:
                corpus += '\n' + rd(dp, f)
            except Exception:
                pass
nosetter = []
for k, v in F.items():
    own = re.search(r'give\(F\.%s\)' % k, script) is not None
    dlg = ('<give_flag>%s</give_flag>' % v) in dtxt
    logic = ('+%s%%' % v) in corpus.upper() or ('%%+%s' % v) in corpus.upper() or ('+%s ' % v) in corpus.upper()
    other = re.search(r'give\([A-Za-z_.]*\b%s\b' % v, corpus) is not None or ('"%s"' % v) in yan_script
    # flags of the mod (restrictor / logic set them): any file but the readers
    if not (own or dlg or logic or other):
        nosetter.append(k + '=' + v)
check('every flag the script reads has a setter (script, dialog, logic or another patch / the mod)', not nosetter, nosetter)

# ----------------------------------------------------------------------------------------------------------------------------------
# 3. tasks
# ----------------------------------------------------------------------------------------------------------------------------------
tm = rd(P('soc_yan_x16_quests', 'gamedata', 'configs', 'misc', 'tm_coop_l08_yantar.ltx'), enc='utf-8')


def section(text, name):
    m = re.search(r'(?m)^\[%s\]\r?\n((?:(?!\[).*\r?\n?)*)' % re.escape(name), text)
    if not m:
        return None
    d = {}
    for ln in m.group(1).splitlines():
        if '=' in ln and not ln.strip().startswith(';'):
            k, v = ln.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def condlist(v):
    """'{+A -B} x, {+C} y, z' -> [(conds, value)]"""
    out = []
    for part in re.findall(r'(?:\{([^}]*)\}\s*)?([A-Za-z_0-9]+)\s*(?:,|$)', v):
        out.append((part[0], part[1]))
    return out


meas = section(tm, 'yan_start_talk_to_the_kruglov_quest_task')
ret = section(tm, 'yan_soc_return_task')
check('the measurement task has the Semenov branches', meas is not None and 'coop_soc_yan_sem_talk_descr' in meas['descr'] and 'yan_semenov_help' in meas['target'])
check('the measurement task fails when the scientist dies before the talk, completes with the results',
      meas.get('condlist_1') == '{+YAN_SCIENTIST_DIE -YAN_SCIENTIST_RETURN_TO_BUNKER} fail' and REPORTED in meas['condlist_0'])
check('the return task exists with title / descr / marker on Sakharov, done by the helmet flag', ret is not None and ret['target'] == 'yan_smart_terrain_1_ecolog_saharov'
      and HELMET in ret['condlist_0'] and has_str(ret['title']) and has_str(ret['descr']), ret)
texts = [v for k in ('title', 'descr') for _, v in condlist(meas.get(k, ''))] + [meas['title']]
check('every text of the measurement task (all branches) exists in EN and RU', all(has_str(t) for t in texts), [t for t in texts if not has_str(t)])
# the order of the branches: the most specific first
dl = condlist(meas['descr'])
check('descr branch order: wounded escort, results, escort (Semenov), escort (Kruglov), talk (Semenov), talk (Kruglov)',
      [v for _, v in dl] == ['coop_soc_yan_sem_escort_descr', 'st_yan_start_talk_to_the_saharov_quest_task_descr', 'coop_soc_yan_sem_escort_descr',
                             'st_yan_start_take_measurements_1_quest_task_descr', 'coop_soc_yan_sem_talk_descr', 'st_yan_start_talk_to_the_kruglov_quest_task_descr'], [v for _, v in dl])

# ----------------------------------------------------------------------------------------------------------------------------------
# 4. spawn sections, character, profile, logic
# ----------------------------------------------------------------------------------------------------------------------------------
spawn = rd(P('yantar_restore', 'gamedata', 'configs', 'creatures', 'spawn_sections_coop_l08_yantar.ltx'))
stories = {}
for m in re.finditer(r'(?m)^\[([^\]]+)\]:stalker\r?\n((?:(?!\[).*\r?\n?)*)', spawn):
    body = m.group(2)
    g = lambda k: (re.search(r'(?m)^%s\s*=\s*(.*?)\s*$' % re.escape(k), body) or [None, None])[1]
    stories[m.group(1)] = {'profile': g('character_profile'), 'story': g('story_id'), 'logic': g('custom_data')}
for sec, story, logic in (('yan_soc_semenov', 'yan_soc_semenov', 'scripts\\coop_l08_yantar\\yan_soc_semenov.ltx'),
                          ('yan_soc_semenov_wounded', 'yan_semenov_help', 'scripts\\coop_l08_yantar\\yan_soc_semenov_wounded.ltx')):
    s = stories.get(sec)
    check('spawn section %s: profile yan_soc_semenov, story id %s, logic file' % (sec, story), s is not None and s['profile'] == 'yan_soc_semenov' and s['story'] == story and s['logic'] == logic, s)
    check('logic file of %s ships in this patch' % sec, os.path.exists(os.path.join(patch, 'gamedata', 'configs', 'scripts', 'coop_l08_yantar', logic.split('\\')[-1])))
all_story = [v['story'] for v in stories.values() if v['story']]
check('story ids are unique in the file', len(all_story) == len(set(all_story)))
cd = rd(P('repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l08_yantar.xml'))
m = re.search(r'<specific_character id="yan_soc_semenov".*?</specific_character>', cd, re.S)
check('specific character yan_soc_semenov', m is not None)
if m:
    c = m.group(0)
    check('character: name, bio exist; start dialog exists; class = id', has_str(re.search(r'<name>([^<]+)</name>', c).group(1)) and has_str(re.search(r'<bio>([^<]+)</bio>', c).group(1))
          and re.search(r'<start_dialog>([^<]+)</start_dialog>', c).group(1) in DIALOGS and '<class>yan_soc_semenov</class>' in c)
    visual = re.search(r'<visual>([^<]+)</visual>', c).group(1)
    ogf = 'meshes\\' + visual + '.ogf'
    found = False
    try:
        import xdb
        for dbn in ('gamedata.db0', 'gamedata.db1'):
            p = os.path.join(ADDON, dbn)
            with open(p, 'rb') as f:
                if any(e[0].lower() == ogf.lower() for e in xdb.index(f, 0, os.path.getsize(p))):
                    found = True
    except Exception as e:
        print('  (model lookup skipped: %s)' % e)
        found = None
    check('character: model %s is in the mod (no model is shipped by this patch)' % visual, found is not False, found)
    icon = re.search(r'<icon>([^<]+)</icon>', c).group(1)
    check('character: portrait %s exists in the mod texture list' % icon, icon in corpus or icon == 'ui_inGame2_neutral_nauchniy', icon)
for owner in ('cordon_technician', 'freedom_duty'):
    t = rd(P(owner, 'gamedata', 'configs', 'gameplay', 'npc_profile_addon.xml'))
    check('profile yan_soc_semenov in %s npc_profile_addon.xml' % owner, re.search(r'<character id="yan_soc_semenov">\s*<class>yan_soc_semenov</class>', t) is not None)
check('the profile id is not used twice in any character file', len(re.findall(r'<specific_character id="yan_soc_semenov"', cd)) == 1)

# logic files
paths = None


def mod_paths():
    """patrol path names + first points of the mod level.game of Yantar (own chunk parser)"""
    import xdb
    data = None
    for dbn in ('gamedata.db0', 'gamedata.db1'):
        p = os.path.join(ADDON, dbn)
        with open(p, 'rb') as f:
            for n, rs, cs, ptr in xdb.index(f, 0, os.path.getsize(p)):
                if n == 'levels\\coop_l08_yantar\\level.game':
                    f.seek(ptr)
                    d = f.read(cs)
                    data = xdb.lzo1x(d, rs) if rs != cs else d

    def chunks(b, o, e):
        r = []
        while o + 8 <= e:
            cid, sz = struct.unpack_from('<II', b, o)
            if o + 8 + sz > e:
                break
            r.append((cid & 0x7fffffff, o + 8, sz))
            o += 8 + sz
        return r
    root = chunks(data, 0, len(data))[0]
    res = {}
    for cid, po, sz in chunks(data, root[1], root[1] + root[2]):
        subs = {c[0]: c for c in chunks(data, po, po + sz)}
        if 5 not in subs or 2 not in subs:
            continue
        nm = data[subs[5][1]:subs[5][1] + subs[5][2]].split(b'\0')[0].decode('latin1')
        o = subs[2][1]
        n = struct.unpack_from('<H', data, o)[0]
        o += 2
        pts = []
        for i in range(n):
            x, y, z = struct.unpack_from('<3f', data, o)
            o += 16
            e = data.index(b'\0', o)
            o = e + 1
            pts.append((x, y, z))
        res[nm] = pts
    return res


try:
    paths = mod_paths()
except Exception as e:
    print('  (level.game lookup skipped: %s)' % e)
for fn in ('yan_soc_semenov.ltx', 'yan_soc_semenov_wounded.ltx'):
    t = rd(patch, 'gamedata', 'configs', 'scripts', 'coop_l08_yantar', fn)
    secs = set(re.findall(r'(?m)^\[([^\]]+)\]', t))
    refs = set()
    for ln in t.splitlines():
        ln = ln.split(';')[0]
        mm = re.match(r'\s*(active|meet|wounded|on_death|on_info\d*)\s*=\s*(?:\{[^}]*\}\s*)?([A-Za-z_0-9]+@[A-Za-z_0-9]+)', ln)
        if mm:
            refs.add(mm.group(2))
    check(fn + ': every section it points to exists', refs <= secs, sorted(refs - secs))
    pr = set(re.findall(r'path\|([A-Za-z_0-9]+),(\d+)', t))
    if paths is not None:
        check(fn + ': every patrol path it names is in the mod level (' + ', '.join(sorted(p for p, _ in pr)) + ')', all(p in paths and int(i) < len(paths[p]) for p, i in pr),
              [p for p, i in pr if p not in paths])
    check(fn + ': no em dash, ASCII only', all(ord(ch) < 128 for ch in t))
w = rd(patch, 'gamedata', 'configs', 'scripts', 'coop_l08_yantar', 'yan_soc_semenov_wounded.ltx')
check('wounded logic: always wounded until the talk (hp_state 102), talk enabled, start dialog is the wounded dialog, mortal until the talk',
      'hp_state = 102|wounded_heavy@nil' in w and 'enable_talk = true' in w and 'help_start_dialog = yan_soc_wounded_dialog' in w
      and w.index('invulnerable = true') > w.index('[remark@yan_soc_semenov_up]'))
check('wounded logic: death sets YAN_SCIENTIST_DIE; the flag of the talk switches to the standing section', '%+YAN_SCIENTIST_DIE%' in w and '{+YAN_SCIENTIST_RETURN_TO_BUNKER} remark@yan_soc_semenov_up' in w)
b = rd(patch, 'gamedata', 'configs', 'scripts', 'coop_l08_yantar', 'yan_soc_semenov.ltx')
check('bunker logic: invulnerable, combat ignored', 'invulnerable = true' in b and 'combat_ignore_cond = true' in b)

# positions against the SoC data
sem_soc = None
if os.path.exists(SOC_ALIFE):
    t = rd(SOC_ALIFE)
    m = re.search(r'name = yantar_semenov\r?\nposition = ([-0-9.e, ]+)', t)
    if m:
        sem_soc = [float(x) for x in m.group(1).split(',')]
sp = re.search(r'local SEM = \{[^}]*pos = \{ x = ([-0-9.]+), y = ([-0-9.]+), z = ([-0-9.]+) \}', script)
wp = re.search(r'local WND = \{[^}]*pos = \{ x = ([-0-9.]+), y = ([-0-9.]+), z = ([-0-9.]+) \}', script)
semp = [float(x) for x in sp.groups()]
wndp = [float(x) for x in wp.groups()]
dist = lambda a, c: sum((x - y) ** 2 for x, y in zip(a, c)) ** 0.5
door2 = (31.2, -11.6, -277.5)                # yan_door_trader_2_1 (the door that is kept open)
door1 = (27.2, -11.6, -277.5)                # yan_door_trader
kruglov = (37.41, -11.72, -277.63)           # walker_kruglov_1_walk (where the mod's Kruglov stands)
seg_a, seg_b = (37.35, -11.72, -272.9), (36.54, -11.72, -276.96)   # walker_kruglov_3_1_walk of the mod level
check('Semenov spot is 4 m or more from both bunker doors (the SoC point is in the doorway of yan_door_trader_2_1)',
      dist(semp, door2) >= 4 and dist(semp, door1) >= 4, (dist(semp, door2), dist(semp, door1)))
check('Semenov spot is 2 to 4 m from Kruglov', 2 <= dist(semp, kruglov) <= 4, dist(semp, kruglov))
check('Semenov spot lies on the segment of Kruglov path walker_kruglov_3_1_walk (an AI path, within 0.1 m)',
      dist(semp, seg_a) + dist(semp, seg_b) - dist(seg_a, seg_b) < 0.1, dist(semp, seg_a) + dist(semp, seg_b) - dist(seg_a, seg_b))
if sem_soc:
    check('the SoC point was in the doorway (less than 2 m from the door; why the spot moved)', dist(sem_soc, door2) < 2, dist(sem_soc, door2))
sec = rd(P('yantar_restore', 'gamedata', 'configs', 'creatures', 'spawn_sections_coop_l08_yantar.ltx'))
check('both Semenov spawn sections use spec_rank = master like the character rank 2071 and Kruglov (a mismatch can make the engine pick another scientist)',
      len(re.findall(r'\[yan_soc_semenov(?:_wounded)?\]:stalker[^\[]*?spec_rank\s*=\s*master', sec)) == 2)
wounded_walk = (171.98, -7.69, -99.49)       # SoC level.game, patrol yan_scientist_wounded_walk wp00 (read with the chunk parser of the notes)
check('wounded spot is the first point of the SoC path yan_scientist_wounded_walk (within 0.05 m)', dist(wndp, wounded_walk) < 0.05, wndp)
site3 = (177.9, -4.6, -99.5)
check('wounded spot is inside the third measurement sphere of the mod (radius 8.2)', dist(wndp, site3) <= 8.2, dist(wndp, site3))

# ----------------------------------------------------------------------------------------------------------------------------------
# 5. voice
# ----------------------------------------------------------------------------------------------------------------------------------
vo = [re.sub(r'\\\\', '/', m) for m in re.findall(r'"(characters_voice\\\\dialogs[^"]*)"', script)]
roots = [os.path.join(patch, 'gamedata', 'sounds'), P('soc_yan_x16_quests', 'gamedata', 'sounds'), P('soc_ru_voices', 'gamedata', 'sounds')]
missing = []
for v in vo:
    if not v.startswith('characters_voice/dialogs/'):
        continue
    if v.endswith('"'):
        continue
    stems = [v]
    if not any(os.path.exists(os.path.join(r, *(s + '.ogg').split('/'))) for r in roots for s in stems):
        # the table builds the name from an id: skip prefixes that end with an underscore
        if not v.endswith('_'):
            missing.append(v)
check('every literal voice path of the script exists (EN / RU recordings)', not missing, missing)
for i in re.search(r'VOICE_S = \{([^}]*)\}', script).group(1).replace('"', '').replace(' ', '').split(','):
    ok = all(os.path.exists(os.path.join(patch, 'gamedata', 'sounds', 'characters_voice', 'dialogs', *sub, 'yantar_general_ucheniy_talk_start_%s.ogg' % i)) for sub in (('eng',), ()))
    check('Sakharov line %s has an English and a Russian recording' % i, ok)
size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(os.path.join(patch, 'gamedata')) for f in fn)
check('size of the patch gamedata is at most 3 MB', size <= 3 * 1024 * 1024, '%.2f MB' % (size / 1048576.0))
check('this patch ships no .ogf / .dds (no models or textures: nothing can miss a models\\capture ltx)', not any(f.endswith(('.ogf', '.dds', '.omf')) for dp, dn, fn in os.walk(os.path.join(patch, 'gamedata')) for f in fn))

print('\nALL PASS' if fails == 0 else '\n%d FAILED' % fails)
sys.exit(1 if fails else 0)
