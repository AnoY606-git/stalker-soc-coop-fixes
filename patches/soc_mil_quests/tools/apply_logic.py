"""Edits the files that other patches own (one patch per file), idempotent. Run again after anything regenerates them.
  python apply_logic.py <mod source dir (has gamedata.db0)>

  freedom_duty:   configs\\gameplay\\dialogs_coop_l07_military.xml   the mod's Lukash / Max / Skull / Cap dialogs out, the SoC dialogs in
                  configs\\gameplay\\character_desc_coop_l07_military.xml   the four NPCs start with the SoC dialog
                  configs\\misc\\tm_coop_l07_military.ltx   SoC task chain (no reward money, no give_task chains: the tick gives the tasks), 3 new steps
                  configs\\scripts\\coop_l07_military\\mil_smart_terrain_14_walker_skull.ltx   (copy of the mod's file) Skull waits for the flag the dialog gives
                  configs\\scripts\\coop_l07_military\\space_restrictors\\mil_cap_pda_1_space_restrictor.ltx   (copy) the zone no longer gives the Cap task
  campfires:      configs\\scripts\\coop_l07_military\\mil_smart_terrain_14_animpoint_duty.ltx   the Duty squad waits for the same flag
  repeatable_quests: configs\\misc\\coop_hidden_tasks.ltx   the tasks that are never given
"""
import os
import re
import shutil
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import mil_model as M
import gen_dialogs as G

repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
P = lambda *a: os.path.join(repo, 'patches', *a)
mod = sys.argv[1] if len(sys.argv) > 1 else None
NL = '\r\n'
changed = []


def rw(path, fn, enc='cp1251'):
    raw = open(path, 'rb').read()
    txt = raw.decode(enc)
    new = fn(txt)
    if new != txt:
        open(path, 'wb').write(new.encode(enc))
        changed.append(os.path.relpath(path, repo))


# ---------------------------------------------------------------------------------------------------
# 1. dialogs
# ---------------------------------------------------------------------------------------------------
def drop_dialog(t, did):
    return re.sub(r'[ \t]*<dialog id="' + re.escape(did) + r'">.*?</dialog>[ \t]*\r?\n', '', t, flags=re.S)


def dialogs(t):
    for d in M.REMOVED_DIALOGS:
        t = drop_dialog(t, d)
    for key, d in M.DIALOGS.items():
        t = drop_dialog(t, d['id'])
    i = t.rindex('</game_dialogs>')
    block = ''.join(G.dialog_xml(k) for k in M.DIALOGS)
    return t[:i] + block + t[i:]


# Max's flash drive job (patch freedom_duty): SoC offers it after the report to Lukash (mil_lukash_dolg_task_complete), not after Skull's death
FLASH_OLD = r'[ \t]*<has_flag>' + M.MAXF + r'</has_flag>[ \t]*\r?\n[ \t]*<has_flag>' + M.SKULL_DEAD + r'</has_flag>'
FLASH_NEW = '        <has_flag>%s</has_flag>' % M.DONE


def flash_gate(t):
    m = re.search(r'<dialog id="mil_smart_terrain_15_freedom_max_flash_offer_dialog">.*?</dialog>', t, re.S)
    blk = m.group(0)
    nb = re.sub(FLASH_OLD, FLASH_NEW, blk)
    return t[:m.start()] + nb + t[m.end():]


rw(P('freedom_duty', 'gamedata', 'configs', 'gameplay', 'dialogs_coop_l07_military.xml'), lambda t: flash_gate(dialogs(t)))


# ---------------------------------------------------------------------------------------------------
# 2. characters
# ---------------------------------------------------------------------------------------------------
def chars(t):
    for name, (start, extra) in M.CHARACTERS.items():
        m = re.search(r'<specific_character id="' + re.escape(name) + r'".*?</specific_character>', t, re.S)
        blk = m.group(0)
        nb = re.sub(r'<start_dialog>[^<]*</start_dialog>', '<start_dialog>%s</start_dialog>' % start, blk)
        for d in M.REMOVED_DIALOGS:
            nb = re.sub(r'[ \t]*<actor_dialog>' + re.escape(d) + r'</actor_dialog>[ \t]*\r?\n', '', nb)
        for e in extra:
            if '<actor_dialog>%s</actor_dialog>' % e not in nb:
                nb = re.sub(r'([ \t]*)(<actor_dialog>actor_break_dialog</actor_dialog>)',
                            lambda mm: mm.group(1) + '<actor_dialog>%s</actor_dialog>' % e + NL + mm.group(1) + mm.group(2), nb, count=1)
        t = t[:m.start()] + nb + t[m.end():]
    return t


rw(P('freedom_duty', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l07_military.xml'), chars)


# ---------------------------------------------------------------------------------------------------
# 3. task sections
# ---------------------------------------------------------------------------------------------------
def sec_span(t, name):
    m = re.search(r'^\[' + re.escape(name) + r'\][^\r\n]*\r?\n', t, re.M)
    if m is None:
        sys.exit('missing task section ' + name)
    n = re.search(r'^\[', t[m.end():], re.M)
    end = m.end() + n.start() if n else len(t)
    return m.end(), end


def set_line(t, sec, key, value):
    a, b = sec_span(t, sec)
    body = t[a:b]
    nb, n = re.subn(r'^(\s*' + re.escape(key) + r'\s*=\s*)[^\r\n]*', lambda mm: mm.group(1) + value, body, flags=re.M)
    if n == 0:
        sys.exit('missing %s in %s' % (key, sec))
    return t[:a] + nb + t[b:]


def del_line(t, sec, key):
    a, b = sec_span(t, sec)
    body = t[a:b]
    nb = re.sub(r'^\s*' + re.escape(key) + r'\s*=[^\r\n]*\r?\n', '', body, flags=re.M)
    return t[:a] + nb + t[b:]


MARK_B = ';;; soc_mil_quests begin (generated by patches\\soc_mil_quests\\tools\\apply_logic.py)'
MARK_E = ';;; soc_mil_quests end'


def tm(t):
    # SoC chains: the tick (coop_soc_mil.script) gives every task to every player, so no give_task chains and no reward_money
    # (SoC pays in the dialogs: Skull 4000 / 8000, Lukash 4000, Cap half of his purse)
    t = set_line(t, 'mil_start_talk_to_the_cap_quest_task', 'condlist_0', '{+%s} complete' % M.CP)
    t = del_line(t, 'mil_start_protect_the_barrier_quest_task', 'reward_money')
    t = set_line(t, 'mil_start_kill_the_sniper_on_the_tower_quest_task', 'condlist_0', '{+%s} complete' % M.SD)
    t = set_line(t, 'mil_start_talk_to_skull_about_the_assault_quest_task', 'condlist_0', '{+%s} complete' % M.ST)
    t = del_line(t, 'mil_start_talk_to_skull_about_the_assault_quest_task', 'condlist_1')
    t = del_line(t, 'mil_start_kill_lukash_quest_task', 'reward_money')
    for i, f in enumerate(M.SNIPER_DEAD, 1):
        s = 'mil_start_kill_the_snipers_%d_quest_task' % i
        t = set_line(t, s, 'condlist_0', '{+%s} complete' % f)
        t = del_line(t, s, 'reward_money')
    t = set_line(t, 'mil_start_report_to_max_quest_task', 'condlist_0', '{+%s} complete' % M.MAXF)
    t = set_line(t, 'mil_start_kill_skull_quest_task', 'condlist_0', '{+%s} complete' % M.DD)
    t = del_line(t, 'mil_start_kill_skull_quest_task', 'reward_money')
    # new steps
    if MARK_B in t:
        t = t[:t.index(MARK_B)].rstrip('\r\n') + NL
    blk = [NL + MARK_B, ';SoC steps that the level maker had no task for (texts: st_coop_soc_mil.xml)']
    for k in M.NEW_TASKS:
        base = 'st_' + k['id'][:-5]
        blk += ['[%s]' % k['id'], 'icon = %s' % k['icon'], 'prior = %d' % k['prior'], 'storyline = %s' % k['storyline'],
                'title = %s_name' % base, 'descr = %s_descr' % base, 'target = %s' % k['target'], 'condlist_0 = %s' % k['cond'], '']
    blk.append(MARK_E)
    return t.rstrip('\r\n') + NL + NL.join(blk) + NL


rw(P('freedom_duty', 'gamedata', 'configs', 'misc', 'tm_coop_l07_military.ltx'), tm)


# ---------------------------------------------------------------------------------------------------
# 4. logic files: the flag that the Skull dialog gives (the mod's logic waits for ..._THE_run_STOP_DIALOG_INFO, which has a lower case part:
#    xr_logic treats a name that is not all upper case as an actor info portion, not a story flag, and nothing ever gives it)
# ---------------------------------------------------------------------------------------------------
BADFLAG = 'MIL_SMART_TERRAIN_18_DUTY_SKULL_TALK_TO_SKULL_ABOUT_THE_run_STOP_DIALOG_INFO'
fix_flag = lambda t: t.replace(BADFLAG, M.ST)
rw(P('campfires', 'gamedata', 'configs', 'scripts', 'coop_l07_military', 'mil_smart_terrain_14_animpoint_duty.ltx'), fix_flag, 'latin-1')


def copy_logic(rel_in_scripts, fn):
    dst = P('freedom_duty', 'gamedata', 'configs', 'scripts', 'coop_l07_military', *rel_in_scripts)
    if not os.path.exists(dst):
        if mod is None:
            sys.exit('need the mod source dir to copy ' + os.path.join(*rel_in_scripts))
        src = os.path.join(mod, 'gamedata.db0', 'configs', 'scripts', 'coop_l07_military', *rel_in_scripts)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        changed.append(os.path.relpath(dst, repo))
    rw(dst, fn, 'latin-1')


copy_logic(['mil_smart_terrain_14_walker_skull.ltx'], fix_flag)
copy_logic(['space_restrictors', 'mil_cap_pda_1_space_restrictor.ltx'], lambda t: t.replace(' =give_task(mil_start_talk_to_the_cap_quest_task)', ''))


# ---------------------------------------------------------------------------------------------------
# 5. hidden tasks
# ---------------------------------------------------------------------------------------------------
def hidden(t):
    have = set(l.strip() for l in t.splitlines())
    miss = [h for h in M.HIDDEN if h not in have]
    if not miss:
        return t
    add = ['', '; Army Warehouses (patch soc_mil_quests): SoC has ONE "Destroy the Duty squad" objective (not Skull + 8 men), 3 snipers (not 4) and no',
           '; "go to the Radar" step on this level (the Radar job comes from the Barkeep).']
    base = t if t.endswith(NL) else t + NL
    return base + NL.join(add + miss) + NL


rw(P('repeatable_quests', 'gamedata', 'configs', 'misc', 'coop_hidden_tasks.ltx'), hidden, 'latin-1')

print('changed:', changed if changed else 'nothing (already applied)')
