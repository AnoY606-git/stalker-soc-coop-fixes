"""Generates everything of patch soc_mil_courier that comes from the ORIGINAL Shadow of Chernobyl data (run once, results are committed):

  python gen_all.py <steam eng text dir> <port rus strings xml> <steam dialogs_military.xml> <steam dialogs_bar.xml>

  <steam eng text dir>   the Steam SoC 1.0006 config\\text\\eng\\*.xml (windows-1251), extracted with tools\\xdb_soc.py
  <port rus strings xml> the Russian SoC strings of the CoP port add-on (utf-8 or windows-1251)
  <steam dialogs_*.xml>  the Steam SoC dialogs (windows-1251)

Writes (all inside the patch folder):
  gamedata\\configs\\text\\eng|rus\\st_coop_soc_milc.xml     the SoC strings under coop_soc_milc_* / mil_soc_* / st_mil_soc_courier_* names
  gamedata\\scripts\\coop_soc_milc_say.script               PDA archive line of every phrase (same helper calls as coop_soc_mil_say.script)
  data\\dialogs_l07_cook.xml        the Chef: start dialog + 12 actor dialogs (converted from the SoC xml, infos -> story flags)
  data\\dialogs_l07_lukash.xml      the Lukash dialog of soc_mil_quests + the courier job (apply_shared.py replaces the block)
  data\\dialogs_l05_voronin.xml     Voronin: the Bulldog 6 order, the hand-in, the suit for a player who was not there
  data\\characters_l07.xml, data\\profiles.xml, data\\spawn_sections.ltx, data\\tm_tasks.ltx
No em dashes, no personal paths in any output."""
import copy
import os
import re
import sys
import xml.etree.ElementTree as ET

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import milc_model as M

patch = os.path.dirname(here)
repo = os.path.dirname(os.path.dirname(patch))
sys.path.insert(0, os.path.join(repo, 'patches', 'soc_mil_quests', 'tools'))
import mil_model as MM          # the model of the Lukash dialog (read only)

if len(sys.argv) != 5:
    sys.exit(__doc__)
eng_dir, rus_file, soc_dlg_mil, soc_dlg_bar = sys.argv[1:5]
NL = '\r\n'


def load_strings(raw):
    try:
        t = raw.decode('utf-8')
    except UnicodeDecodeError:
        t = raw.decode('cp1251', errors='replace')
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'<string id="([^"]*)">\s*<text>(.*?)</text>', t, re.S)}


ENG = {}
for f in sorted(os.listdir(eng_dir)):
    if f.endswith('.xml'):
        ENG.update(load_strings(open(os.path.join(eng_dir, f), 'rb').read()))
RUS = load_strings(open(rus_file, 'rb').read())


def src_text(sid):
    for lang, d in (('eng', ENG), ('rus', RUS)):
        if sid not in d:
            sys.exit('missing SoC string %s (%s)' % (sid, lang))
    return ENG[sid], RUS[sid]


# ---------------------------------------------------------------------------------------------------
# SoC dialogs -> phrase dicts
# ---------------------------------------------------------------------------------------------------
def soc_dialogs(path):
    root = ET.fromstring(open(path, 'rb').read())
    out = {}
    for d in root.findall('dialog'):
        ph = {}
        for p in d.find('phrase_list').findall('phrase'):
            t = p.find('text')
            ph[p.get('id')] = dict(text=(t.text.strip() if t is not None and t.text else ''),
                                   nxt=[x.text.strip() for x in p.findall('next')],
                                   give=[x.text.strip() for x in p.findall('give_info')],
                                   has=[x.text.strip() for x in p.findall('has_info')],
                                   dont=[x.text.strip() for x in p.findall('dont_has_info')],
                                   act=[x.text.strip() for x in p.findall('action')],
                                   pre=[x.text.strip() for x in p.findall('precondition')])
        out[d.get('id')] = dict(
            has=[x.text.strip() for x in d.findall('has_info')], dont=[x.text.strip() for x in d.findall('dont_has_info')],
            pre=[x.text.strip() for x in d.findall('precondition')], phrases=ph)
    return out


SOC_MIL = soc_dialogs(soc_dlg_mil)
SOC_BAR = soc_dialogs(soc_dlg_bar)


def flag_of(info):
    if info not in M.INFO:
        sys.exit('SoC info portion without a flag: ' + info)
    return M.INFO[info]


def uniq(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def convert(src, table):
    """SoC actor dialog -> dict(id, key, has, dont, pre, phrases=[M.P dict + 'text_src'])"""
    d = table[src]
    key = M.short(src)
    # speaker by depth from phrase 0 (an actor dialog: the actor speaks first)
    depth = {'0': 0}
    todo = ['0']
    while todo:
        p = todo.pop(0)
        for n in d['phrases'][p]['nxt']:
            if n not in depth:
                depth[n] = depth[p] + 1
                todo.append(n)
    phrases = []
    for pid, p in d['phrases'].items():
        if pid not in depth:
            sys.exit('phrase %s of %s is not reachable from 0' % (pid, src))
        pre = []
        for x in p['pre']:
            if x not in M.PRE_MAP:
                sys.exit('unmapped precondition ' + x)
            if M.PRE_MAP[x]:
                pre.append(M.PRE_MAP[x])
        acts = []
        for x in p['act']:
            if x not in M.ACT_MAP:
                sys.exit('unmapped action ' + x)
            acts.append(M.ACT_MAP[x])
        ph = M.P(pid, M.A if depth[pid] % 2 == 0 else M.N, p['nxt'], pre, uniq(flag_of(i) for i in p['give']), acts,
                 uniq(flag_of(i) for i in p['has']), uniq(flag_of(i) for i in p['dont']))
        ph['text_src'] = '%s_%s' % (src, pid)
        phrases.append(ph)
    pre = []
    for x in d['pre']:
        if x not in M.PRE_MAP:
            sys.exit('unmapped dialog precondition ' + x)
        if M.PRE_MAP[x]:
            pre.append(M.PRE_MAP[x])
    return dict(id=M.new_id(src), key=key, has=uniq(flag_of(i) for i in d['has']), dont=uniq(flag_of(i) for i in d['dont']), pre=pre,
                phrases=phrases)


DIALOGS = []         # every dialog written by this generator, in order
COOK = [convert(s, SOC_MIL) for s in M.COOK_DIALOGS]
# the Chef's greeting (SoC meet_dialog mil_cook_dialog, one phrase)
cook_start = dict(id='mil_soc_cook_dialog', key='ck_start', has=[], dont=[], pre=[], phrases=[
    dict(M.P('0', M.N), text_src='mil_cook_dialog_0')])
VOR = [convert(s, SOC_BAR) for s in M.VORONIN_DIALOGS]
# the suit for a player who was not the one that handed the weapon in (the Bulldog 6 is delivered, the flag is shared)
fin = [v for v in VOR if v['key'] == 'vo_quest_rg6_finish'][0]
late = dict(id='mil_soc_dolg_leader_rg6_late', key='vo_late', has=[M.RDONE], dont=[], pre=[M.MILC + '.suit_pending'], phrases=[
    dict(M.P('0', M.A, ['1']), text_src='bar_dolg_leader_quest_rg6_finish_0'),
    dict(M.P('1', M.N, [], [], [], [M.MILC + '.give_suit']), text_src='bar_dolg_leader_quest_rg6_finish_1')])
VOR.append(late)

# ---------------------------------------------------------------------------------------------------
# Lukash: the dialog of soc_mil_quests + the courier job
# ---------------------------------------------------------------------------------------------------
lu_old = MM.DIALOGS['lu']
lu_phrases = []
old_ids = set()
for pid, spk, nxt, pre, flags, acts in lu_old['phrases']:
    old_ids.add(pid)
    ph = M.P(pid, spk, nxt, [M.MIL + '.' + x for x in pre], flags, [M.MIL + '.' + x for x in acts])
    ph['ns'] = 'mil'
    if pid in M.LUKASH_CHANGE:
        for k, v in M.LUKASH_CHANGE[pid].items():
            ph[k] = list(v)
    if pid == '0':
        ph['nxt'] = ph['nxt'] + M.LUKASH_ROOT_EXTRA
    lu_phrases.append(ph)
for ph in M.LUKASH_NEW:
    ph = copy.deepcopy(ph)
    if ph['id'] in old_ids:
        sys.exit('new Lukash phrase %s exists already' % ph['id'])
    ph['ns'] = 'milc'
    ph['text_src'] = 'mil_leader_start_dialog_' + ph['id']
    ph['acts'] = [M.MILC + '.' + a if '.' not in a else a for a in ph['acts']]
    lu_phrases.append(ph)
LUKASH = dict(id=M.LUKASH_DIALOG, key='lu', has=[], dont=[], pre=[], phrases=lu_phrases)

# ---------------------------------------------------------------------------------------------------
# dialog xml + say script + strings
# ---------------------------------------------------------------------------------------------------
TEXT = {}       # new id -> (eng, rus)
SAY = []        # (script id, speaker)


def text_id(d, ph):
    if ph.get('ns') == 'mil':
        return 'coop_soc_mil_lu_' + ph['id'], 'coop_soc_mil_say.say_lu_' + ph['id']
    sid = '%s_%s' % (d['key'], ph['id'])
    return 'coop_soc_milc_' + sid, 'coop_soc_milc_say.say_' + sid


def phrase_xml(d, ph):
    s = ['            <phrase id="%s">' % ph['id']]
    if ph['spk'] == M.H:
        s.append('                <text />')
    else:
        tid, say = text_id(d, ph)
        s.append('                <action>%s</action>' % say)
        s.append('                <text>%s</text>' % tid)
        if ph.get('ns') != 'mil':
            TEXT[tid] = src_text(ph['text_src'])
            SAY.append(('%s_%s' % (d['key'], ph['id']), ph['spk']))
    for h in ph['has']:
        s.append('                <has_flag>%s</has_flag>' % h)
    for h in ph['dont']:
        s.append('                <dont_has_flag>%s</dont_has_flag>' % h)
    for p in ph['pre']:
        s.append('                <precondition>%s</precondition>' % p)
    for a in ph['acts']:
        s.append('                <action>%s</action>' % a)
    for f in ph['flags']:
        s.append('                <give_flag>%s</give_flag>' % f)
    if not ph['nxt'] and ph['spk'] != M.H:
        s.append('                <action>dialogs.break_dialog</action>')
    for n in ph['nxt']:
        s.append('                <next>%s</next>' % n)
    s.append('            </phrase>')
    return s


def dialog_xml(d):
    L = ['    <dialog id="%s">' % d['id']]
    for p in d['pre']:
        L.append('        <precondition>%s</precondition>' % p)
    for h in d['has']:
        L.append('        <has_flag>%s</has_flag>' % h)
    for h in d['dont']:
        L.append('        <dont_has_flag>%s</dont_has_flag>' % h)
    L.append('        <phrase_list>')
    for ph in d['phrases']:
        L += phrase_xml(d, ph)
    L += ['        </phrase_list>', '    </dialog>']
    return NL.join(L) + NL


def write(rel, txt, enc='cp1251'):
    path = os.path.join(patch, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    assert chr(0x2014) not in txt, 'em dash in ' + rel
    with open(path, 'wb') as f:
        f.write(txt.encode(enc, errors='replace'))
    print('wrote', rel, len(txt))


write('data/dialogs_l07_cook.xml', ''.join(dialog_xml(d) for d in [cook_start] + COOK))
write('data/dialogs_l07_lukash.xml', dialog_xml(LUKASH))
write('data/dialogs_l05_voronin.xml', ''.join(dialog_xml(d) for d in VOR))

# ---------------------------------------------------------------------------------------------------
# characters / profiles / sections / tasks
# ---------------------------------------------------------------------------------------------------


def supplies_block(items, includes):
    s = ['    <supplies>', '      [spawn] \\n']
    for i in items:
        s.append('      %s \\n' % i)
    s.append('')
    for inc in includes:
        s.append('#include "gameplay\\%s"' % inc)
    s.append('    </supplies>')
    return s


FREEDOM_INC = ['character_items_nd.xml', 'character_food.xml', 'character_drugs_3.xml', 'character_drugs_sci.xml', 'character_drugs_mil.xml']
KILLER_INC = ['character_items_nd.xml', 'character_food.xml', 'character_drugs.xml']


def char_xml(cid, name, icon, bio, community, rank, rep, visual, snd, items, includes, start=None, actors=(), tail=()):
    L = ['<specific_character id="%s" team_default = "1">' % cid,
         '    <name>%s</name>' % name, '    <icon>%s</icon>' % icon, '    <map_icon x="0" y="6"></map_icon>', '    <bio>%s</bio>' % bio,
         '    <class>%s</class>' % cid,
         '    <community>%s</community> <terrain_sect>stalker_terrain</terrain_sect>' % community,
         '    <money min="1000000" max="2000000" infinitive="1"></money>', '    <rank>%d</rank>' % rank, '    <reputation>%d</reputation>' % rep,
         '    <visual>%s</visual>' % visual, '    <snd_config>%s</snd_config>' % snd, '    <crouch_type>-1</crouch_type>']
    L += supplies_block(items, includes)
    L += list(tail)
    if start:
        L.append('    <start_dialog>%s</start_dialog>' % start)
    for a in actors:
        L.append('    <actor_dialog>%s</actor_dialog>' % a)
    L.append('</specific_character>')
    return NL.join(L) + NL


chars = ''
for key in ('pavlik', 'ara', 'cook'):
    n = M.NPCS[key]
    inc = KILLER_INC if n['community'] == 'killer' else FREEDOM_INC
    actors = []
    start = None
    if key == 'cook':
        start = 'mil_soc_cook_dialog'
        actors = [d['id'] for d in COOK]
    chars += char_xml(n['profile'], n['name'], n['icon'], n['bio'], n['community'], n['rank_n'], n['rep'], n['visual'], n['snd'],
                      n['supplies'], inc, start, actors + ['actor_break_dialog'] if key == 'cook' else ())
g = M.GUARD_CHAR
chars += char_xml(g['profile'], 'GENERATE_NAME_stalker', g['icon'], 'none', 'killer', g['rank_n'], g['rep'], g['visual'], g['snd'],
                  g['supplies'], KILLER_INC)
write('data/characters_l07.xml', chars)

prof = ''
for pid in ('mil_soc_pavlik', 'mil_soc_ara', 'mil_soc_ara_guard', 'mil_soc_cook'):
    prof += '\t<character id="%s">%s\t\t<class>%s</class>%s\t</character>%s' % (pid, NL, pid, NL, NL)
write('data/profiles.xml', prof)

sect = []
for key in ('pavlik', 'ara', 'g1', 'g2', 'g3', 'cook'):
    n = M.NPCS[key]
    sect += ['[%s]:stalker' % n['section'], '$spawn\t\t\t\t\t\t= "respawn\\%s"' % n['section'], 'character_profile\t\t\t= %s' % n['profile'],
             'spec_rank\t\t\t\t\t= %s' % n['rank'], 'community\t\t\t\t\t= %s' % n['community'], 'story_id\t\t\t\t\t= %s' % n['story'],
             'custom_data\t\t\t\t\t= scripts\\coop_l07_military\\%s' % n['logic'], '']
write('data/spawn_sections.ltx', NL.join(sect), 'latin-1')

tm = []
for t in M.TASKS:
    base = 'st_' + t['id'][:-5]
    tm += ['[%s]' % t['id'], 'icon = %s' % t['icon'], 'prior = %d' % t['prior'], 'storyline = %s' % t['storyline'],
           'title = %s_name' % base, 'descr = %s_descr' % base, 'target = %s' % t['target']]
    for i, c in enumerate(t['conds']):
        tm.append('condlist_%d = %s' % (i, c))
    tm.append('')
write('data/tm_tasks.ltx', NL.join(tm), 'latin-1')

# ---------------------------------------------------------------------------------------------------
# strings
# ---------------------------------------------------------------------------------------------------
for key in ('pavlik', 'ara', 'cook'):
    n = M.NPCS[key]
    TEXT[n['name']] = src_text(n['soc_char'] + '_name')
    TEXT[n['bio']] = src_text(n['soc_char'] + '_bio')
for t in M.TASKS:
    base = 'st_' + t['id'][:-5]
    e1, r1 = src_text(t['title'])
    e2, r2 = src_text(t['obj'])
    if t['article']:
        e3, r3 = src_text(t['article'])
        e2, r2 = e2 + '\\n\\n' + e3, r2 + '\\n\\n' + r3
    TEXT[base + '_name'] = (e1, r1)
    TEXT[base + '_descr'] = (e2, r2)
TEXT['st_mil_soc_lang_probe'] = ('Language', 'Язык')

for idx, lang in ((0, 'eng'), (1, 'rus')):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for k in sorted(TEXT):
        lines.append('\t<string id="%s"><text>%s</text></string>' % (k, TEXT[k][idx]))
    lines.append('</string_table>')
    out = NL.join(lines) + NL
    bad = sorted(set(c for c in out if ord(c) > 127)) if lang == 'eng' else []
    if bad:
        print('WARN non-ascii in eng:', ''.join(bad))
        out = out.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('…', '...')
    write('gamedata/configs/text/%s/st_coop_soc_milc.xml' % lang, out)

# ---------------------------------------------------------------------------------------------------
# PDA archive script
# ---------------------------------------------------------------------------------------------------
L = ['-------------------------------------------------------------------------------------------------------',
     '-- GENERATED by patches\\soc_mil_courier\\tools\\gen_all.py: the PDA archive line of every phrase of the courier / Bulldog 6 dialogs',
     '-- (Lukash additions, Chef, Voronin). Same helper calls as coop_soc_mil_say.script.',
     '-------------------------------------------------------------------------------------------------------', '', 'local SPEAKER = {']
for sid, spk in SAY:
    L.append('\t%s = "%s",' % (sid, spk))
L += ['}', '', 'local function emit(id, first, second)', '\tlocal tid = "coop_soc_milc_" .. id',
      '\tpcall(function() coop_pda_phrases.phrase_speaker[tid] = SPEAKER[id] end)',
      '\tpcall(function() coop_pda_archive_sync.emit_phrase(first, second, tid) end)', 'end', '']
for sid, spk in SAY:
    L.append('function say_%s(a, b) emit("%s", a, b) end' % (sid, sid))
write('gamedata/scripts/coop_soc_milc_say.script', '\n'.join(L) + '\n', 'ascii')
print('phrases with text:', len(SAY), 'strings:', len(TEXT))
