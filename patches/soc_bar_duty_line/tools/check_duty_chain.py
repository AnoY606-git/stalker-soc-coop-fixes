"""Static proof of the Bar Duty / Freedom line (patch soc_bar_duty_line). Prints PROBLEM lines; exit code 1 when there are any.
  python -I check_duty_chain.py <mod source gamedata.db0 dir> [--shared <repo dir>]

Reads the generated files of the patch (dialogs, text, characters, profiles, spawn sections, tasks, scripts) and checks:
  * every phrase of every dialog: the text id exists in eng + rus, next ids exist, preconditions / actions name functions that exist in
    coop_soc_duty.script, a say_ function exists in coop_soc_duty_say.script, hidden phrases lead somewhere
  * dialog ids used by characters exist (new file, mod files or the stock list), every new character has a profile and a spawn section
  * every flag a dialog gives or a task reads is a flag the script knows (name table F of the script)
  * the task sections: ids = the STAGES of the script, titles / descriptions exist in both languages, target story ids belong to a known NPC
  * the NPC table of the script equals duty_model (positions, sections, levels, story ids)
  * with --shared <dir>: the tree after tools\\apply_shared.py registers the new files and gives the dialogs to the characters
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import duty_model as M

patch = os.path.dirname(here)
GD = os.path.join(patch, 'gamedata')
mod = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else None
shared = sys.argv[sys.argv.index('--shared') + 1] if '--shared' in sys.argv else None
problems = []


def bad(msg):
    problems.append(msg)
    print('PROBLEM', msg)


def rd(*a):
    return open(os.path.join(GD, *a), 'rb').read()


script = rd('scripts', 'coop_soc_duty.script').decode('ascii')
say = rd('scripts', 'coop_soc_duty_say.script').decode('ascii')
funcs = set(re.findall(r'^function\s+([A-Za-z_][A-Za-z0-9_]*)', script, re.M))
sayf = set(re.findall(r'^function\s+([A-Za-z_][A-Za-z0-9_]*)', say, re.M))

# ---- flag table of the script
F = dict(re.findall(r'(\w+)\s*=\s*"([A-Z0-9_]+)"', script[:script.index('local ARENA_PULSE')]))
FLAGS = set(F.values())
for name in ('PASS', 'CSTART', 'CLEAD', 'TSTART', 'ARENA', 'TDONE', 'RSTART', 'RGAIN', 'RDONE', 'OATH', 'KSTART', 'KKILLED', 'KDONE', 'VSTART', 'VKILLED',
             'VDONE', 'ASTART', 'AKILLED', 'ADONE', 'LPDA', 'TPDA', 'RMADE', 'AGR_DONE', 'LUKASH_DEAD'):
    if F.get(name) != getattr(M, name):
        bad('flag %s: script %r, model %r' % (name, F.get(name), getattr(M, name)))

# ---- texts
def texts(lang):
    t = rd('configs', 'text', lang, 'st_coop_soc_duty.xml').decode('cp1251')
    return dict(re.findall(r'<string id="([^"]+)"><text>(.*?)</text></string>', t))

ENG, RUS = texts('eng'), texts('rus')
for k in ENG:
    if k not in RUS:
        bad('text %s missing in rus' % k)
    if chr(0x2014) in ENG[k] or chr(0x2014) in RUS.get(k, ''):
        bad('em dash in %s' % k)

# ---- dialogs
dlg_xml = ET.fromstring(rd('configs', 'gameplay', 'dialogs_coop_soc_duty.xml'))
dialog_ids = set()
nphr = 0
for d in dlg_xml.findall('dialog'):
    did = d.get('id')
    dialog_ids.add(did)
    for pre in d.findall('precondition'):
        fn = pre.text.split('.')[1]
        if fn not in funcs:
            bad('%s: dialog precondition %s missing' % (did, pre.text))
    ph = {p.get('id'): p for p in d.find('phrase_list').findall('phrase')}
    for pid, p in ph.items():
        nphr += 1
        txt = (p.findtext('text') or '').strip()
        if txt:
            if txt not in ENG or txt not in RUS:
                bad('%s/%s: text %s missing' % (did, pid, txt))
            sa = [a.text for a in p.findall('action') if a.text.startswith('coop_soc_duty_say.')]
            if not sa or sa[0].split('.')[1] not in sayf:
                bad('%s/%s: no say_ action / function' % (did, pid))
        else:
            if not p.findall('next'):
                bad('%s/%s: hidden phrase without next' % (did, pid))
        for x in p.findall('precondition') + p.findall('action'):
            mod_, fn = x.text.split('.')
            if mod_ == 'coop_soc_duty' and fn not in funcs:
                bad('%s/%s: function %s missing' % (did, pid, x.text))
        for n in p.findall('next'):
            if n.text not in ph:
                bad('%s/%s: next %s missing' % (did, pid, n.text))
        for g in p.findall('give_flag'):
            if g.text not in FLAGS:
                bad('%s/%s: flag %s unknown to the script' % (did, pid, g.text))
# reachability: every phrase is reachable from "0"
for d in dlg_xml.findall('dialog'):
    ph = {p.get('id'): p for p in d.find('phrase_list').findall('phrase')}
    seen, todo = set(), ['0']
    while todo:
        x = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        todo += [n.text for n in ph[x].findall('next')]
    for pid in ph:
        if pid not in seen:
            bad('%s/%s: unreachable phrase' % (d.get('id'), pid))
print('dialogs: %d, phrases: %d' % (len(dialog_ids), nphr))

# ---- characters, profiles, sections
chars = rd('configs', 'gameplay', 'character_desc_coop_soc_duty.xml').decode('cp1251')
prof = rd('configs', 'gameplay', 'npc_profile_coop_soc_duty.xml').decode('utf-8')
spawn = rd('configs', 'creatures', 'spawn_sections_coop_l06_rostok.ltx').decode('ascii')
char_ids = re.findall(r'<specific_character id="([^"]+)"', chars)
for cid in char_ids:
    if '<character id="%s">' % cid not in prof:
        bad('character %s has no profile' % cid)
for sec in re.findall(r'^\[(soc_[a-z0-9_]+)\]:stalker', spawn, re.M):
    m = re.search(r'^\[%s\]:stalker.*?character_profile\s*=\s*(\S+)' % sec, spawn, re.M | re.S)
    if m.group(1) not in char_ids:
        bad('section %s: profile %s has no specific character' % (sec, m.group(1)))
for m in re.finditer(r'<(start_dialog|actor_dialog)>([^<]+)<', chars):
    if m.group(2) not in dialog_ids and m.group(2) != 'actor_break_dialog':
        bad('character dialog %s unknown' % m.group(2))
for key, (start, acts) in list(M.SHARED_CHARACTERS.items()) + list(M.NEW_DIALOG_CHARS.items()):
    for x in ([start] if start else []) + acts:
        if x not in dialog_ids:
            bad('%s: dialog %s not in the dialog file' % (key, x))
for sec in re.findall(r'custom_data\s*=\s*(\S+)', spawn):
    if not os.path.exists(os.path.join(GD, 'configs', sec.replace(chr(92), os.sep))):
        bad('custom_data file %s missing' % sec)
for t in ('bar_lucky_pda', 'bar_tiran_pda'):
    if '[%s]:quest_item_base' % t not in spawn:
        bad('item section %s missing' % t)
for ref in re.findall(r'(?:description|inv_name|inv_name_short)\s*=\s*(coop_soc_duty_\w+)', spawn):
    if ref not in ENG:
        bad('item text %s missing' % ref)
for ref in re.findall(r'<(?:name|bio)>(coop_soc_duty_\w+)<', chars):
    if ref not in ENG:
        bad('character text %s missing' % ref)

# ---- NPC table of the script == model
rows = re.findall(r'\{ key = "(\w+)", level = "(\w+)", section = "(\w+)", story = ("?[\w]+"?), x = (-?[\d.]+), y = (-?[\d.]+), z = (-?[\d.]+), hostile = (true|false)(?:, need = F\.(\w+))? \}', script)
if len(rows) != len(M.NPCS):
    bad('NPC table: %d rows in the script, %d in the model' % (len(rows), len(M.NPCS)))
for r, n in zip(rows, M.NPCS):
    key, level, section, story, x, y, z, hostile, need = r
    exp = (n['key'], n['level'], n['section'], '"%s"' % n['story'] if n['story'] else 'nil', n['pos'], n['hostile'], n.get('need'))
    got = (key, level, section, story, (float(x), float(y), float(z)), hostile == 'true', F.get(need) if need else None)
    if exp != got:
        bad('NPC %s differs: model %r script %r' % (n['key'], exp, got))
    if n['section'] not in spawn:
        bad('NPC %s: spawn section missing' % n['key'])
m = re.search(r'local RG6_POS = \{ level = "(\w+)", x = (-?[\d.]+), y = (-?[\d.]+), z = (-?[\d.]+) \}', script)
if (m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))) != (M.RG6['level'], ) + tuple(M.RG6['pos']):
    bad('RG-6 position differs')

# ---- tasks
tm = rd('configs', 'misc', 'tm_coop_soc_duty.ltx').decode('ascii')
tasks = re.findall(r'^\[(\w+)\]', tm, re.M)
stages = re.findall(r'\{ id = "(\w+)", open', script)
if tasks != stages:
    bad('tm tasks %s != script stages %s' % (tasks, stages))
known_story = set(M.NPC.values()) | {M.RG6_STORY}
for sec in re.finditer(r'^\[(\w+)\]\n(.*?)(?=^\[|\Z)', tm.replace('\r\n', '\n'), re.M | re.S):
    tid, body = sec.group(1), sec.group(2)
    kv = dict(re.findall(r'^(\w+)\s*=\s*(.*)$', body, re.M))
    for k in ('title', 'descr'):
        for ref in re.findall(r'coop_soc_duty_\w+', kv[k]):
            if ref not in ENG or ref not in RUS:
                bad('%s: text %s missing' % (tid, ref))
    for st in re.sub(r'\{[^}]*\}', '', kv['target']).split(','):
        st = st.strip()
        if st and st not in known_story:
            bad('%s: target %s is no known story id' % (tid, st))
    for fl in re.findall(r'[+-]([A-Z0-9_]+)', ' '.join(re.findall(r'\{[^}]*\}', body))):
        if fl not in FLAGS:
            bad('%s: flag %s unknown to the script' % (tid, fl))
    if 'condlist_0' not in kv or 'complete' not in kv['condlist_0']:
        bad('%s: no completion' % tid)

# ---- the shared edits (after apply_shared)
if shared:
    s = open(os.path.join(shared, 'patches', 'repeatable_quests', 'gamedata', 'configs', 'system.ltx'), 'rb').read().decode('latin1')
    for n in ('dialogs_coop_soc_duty', 'character_desc_coop_soc_duty', 'npc_profile_coop_soc_duty'):
        if n not in s:
            bad('system.ltx does not register %s' % n)
    tmn = open(os.path.join(shared, 'patches', 'repeatable_quests', 'gamedata', 'configs', 'misc', 'task_manager.ltx'), 'rb').read().decode('latin1')
    if '#include "tm_coop_soc_duty.ltx"' not in tmn:
        bad('task_manager.ltx lacks the include')
    cd = open(os.path.join(shared, 'patches', 'repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l05_bar.xml'), 'rb').read().decode('cp1251')
    for cid, (start, acts) in M.SHARED_CHARACTERS.items():
        m = re.search(r'<specific_character id="%s".*?</specific_character>' % cid, cd, re.S)
        if not m:
            bad('character %s missing in the shared file' % cid)
            continue
        if start and '<start_dialog>%s</start_dialog>' % start not in m.group(0):
            bad('%s does not start with %s' % (cid, start))
        for a in acts:
            if '<actor_dialog>%s</actor_dialog>' % a not in m.group(0):
                bad('%s lacks actor dialog %s' % (cid, a))

print('%d problems' % len(problems))
sys.exit(1 if problems else 0)
