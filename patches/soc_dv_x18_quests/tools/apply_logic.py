"""Task sections, level logic and hidden tasks of the SoC Dark Valley / X18 chain (idempotent).

  python apply_logic.py [<mod source gamedata.db0 dir>]

  1. patches\\darkvalley_restore\\...\\misc\\tm_coop_l04_darkvalley.ltx  the task file of Dark Valley (that patch owns it)
  2. patches\\darkvalley_restore\\...\\x18_start_get_out_of_the_lab_quest_task_space_restrictor.ltx  the raid starts when the documents are found
  3. patches\\repeatable_quests\\...\\misc\\coop_hidden_tasks.ltx  the mod-only tasks are never given
  4. new copies (this patch) of three level logic files of the mod: both code doors, Bullet, and the Bar start restrictor
"""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
if len(sys.argv) < 2:
    sys.exit('usage: apply_logic.py <mod source gamedata.db0 dir>')
mod = sys.argv[1]
P = lambda *a: os.path.join(repo, 'patches', *a)
changed = []


def write(path, data):
    old = open(path, 'rb').read() if os.path.exists(path) else None
    if old != data:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
        changed.append(os.path.relpath(path, repo))


# ---------------------------------------------------------------------------------------------------
# 1. tm_coop_l04_darkvalley.ltx
# ---------------------------------------------------------------------------------------------------
tm_path = P('darkvalley_restore', 'gamedata', 'configs', 'misc', 'tm_coop_l04_darkvalley.ltx')
tm = open(tm_path, 'rb').read().decode('cp1251')
nl = '\r\n' if '\r\n' in tm else '\n'
tm = tm.replace('\r\n', '\n')


def kv(key, value):
    return '%-40s= %s' % (key, value)


def make(name, comment, lines):
    return '%s[%s]\n%s\n' % (('; ' + comment + '\n') if comment else '', name, '\n'.join(kv(k, v) for k, v in lines))


def put(name, comment, lines):
    """replace (header, the comment lines right above it, key lines) or append one section"""
    global tm
    body = make(name, comment, lines).rstrip('\n').split('\n')
    L = tm.split('\n')
    h = next((i for i, x in enumerate(L) if x.strip() == '[' + name + ']'), None)
    if h is None:
        while L and L[-1].strip() == '':
            L.pop()
        L += [''] + body + ['']
    else:
        start = h
        while start > 0 and L[start - 1].startswith(';'):
            start -= 1
        end = h + 1
        while end < len(L) and not L[end].startswith('['):
            end += 1
        while end - 1 > h and (L[end - 1].strip() == '' or L[end - 1].startswith(';')):
            end -= 1
        L[start:end] = body
    tm = '\n'.join(L)


# documents (SoC bar_darklab_documents2): found by the party, then brought to the BARKEEP (not Sidorovich)
put('val_start_sneak_into_the_x_18_lab_1_quest_task', 'SoC bar_darklab_documents2, objective 1 "Find the documents" (started on entering the lab); done when the party holds all X18 documents', [
    ('icon', 'ui_inGame2_val_start_sneak_into_the_x_18_lab_1_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_val_start_sneak_into_the_x_18_lab_1_quest_task_name'), ('descr', 'st_val_start_sneak_into_the_x_18_lab_1_quest_task_descr'),
    ('target', 'nil'), ('condlist_0', '{+BAR_DARKLAB_DOCUMENT_GAIN} complete')])
put('val_start_take_the_documents_to_the_barmen_quest_task', 'SoC bar_darklab_documents2, objective 2 "Bring the documents to the Barkeep"', [
    ('icon', 'ui_inGame2_val_start_take_the_documents_to_the_barmen_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_val_start_take_the_documents_to_the_barmen_quest_task_name'), ('descr', 'st_val_start_take_the_documents_to_the_barmen_quest_task_descr'),
    ('target', 'bar_smart_terrain_1_stalker_barmen'),
    ('condlist_0', '{+BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} complete')])
# Bullet: the two objectives of SoC val_captive_help; the tick of coop_soc_dv.script hands both to every player
put('val_start_follow_the_bullet_quest_task', 'SoC val_captive_help, objective 1 (given by coop_soc_dv.script to every player once Bullet asks, flag VAL_ESCORT_TASK_START)', [
    ('icon', 'ui_inGame2_val_start_follow_the_bullet_quest_task'), ('prior', '100'), ('storyline', 'true'),
    ('title', 'st_val_start_follow_the_bullet_quest_task_name'), ('descr', 'st_val_start_follow_the_bullet_quest_task_descr'),
    ('target', 'val_smart_terrain_18_duty_bullet_squad'),
    ('condlist_0', '{+VAL_SMART_TERRAIN_19_SPAWN_SQUAD_SPACE_RESTRICTOR_INFO} complete'),
    ('condlist_1', '{+VAL_SMART_TERRAIN_18_DUTY_BULLET_SQUAD_DEAD} fail')])
# the way out: SoC val_come_to_trader; it fails when the documents are done at the Barkeep; Sidorovich takes no documents
put('val_start_get_out_via_south_gate_quest_task', 'SoC val_come_to_trader: "Get out of the Dark Valley" (fails when the X18 documents are handed to the Barkeep)', [
    ('icon', 'ui_inGame2_val_start_take_the_documents_to_the_barmen_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_val_start_get_out_via_south_gate_quest_task_name'), ('descr', 'st_val_start_get_out_via_south_gate_quest_task_descr'),
    ('target', 'val_esc_level_changer'),
    ('condlist_0', '{+ESC_RETURN_FROM_DV_INFO} complete'),
    ('condlist_1', '{+BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} fail')])
# the old Sidorovich step stays defined for old saves but is hidden (coop_hidden_tasks.ltx)
put('val_start_show_documents_to_sidorovich_quest_task', 'hidden: in SoC the documents go to the Barkeep (kept so that an old save can still load)', [
    ('icon', 'ui_inGame2_val_start_take_the_documents_to_the_barmen_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_val_start_show_documents_to_sidorovich_quest_task_name'), ('descr', 'st_val_start_show_documents_to_sidorovich_quest_task_descr'),
    ('target', 'esc_smart_terrain_1_trader_sidorovich'),
    ('condlist_0', '{+ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_X18_DOCUMENTS_STOP_DIALOG_INFO} complete'),
    ('condlist_1', '{+BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO} fail')])

# the four objectives of SoC bar_darklab_documents (Barkeep job): sneak into the base, Borov's key, get out, find the entrance
for i, (cond, target, oname) in enumerate([
        ('{+VAL_ACTOR_ON_BANDITS_BASE} complete', 'val_smart_terrain_4_bandit_borov', 'objective 4 "Sneak into the base"'),
        ('{+VAL_ACTOR_HAS_BOROV_KEY} complete', 'val_smart_terrain_4_bandit_borov', 'objective 1 "Take the key to the lab from Borov"'),
        ('{+VAL_ACTOR_LEAVE_BANDITS_BASE} complete', 'val_x18_level_changer', 'objective 2 "Get out of the bandit base"'),
        ('{+VAL_X18_DOOR_OPEN} complete', 'val_x18_level_changer', 'objective 3 "Find the entrance to the lab"')], 1):
    put('val_soc_darklab_%d_task' % i, 'SoC bar_darklab_documents, %s' % oname, [
        ('icon', 'ui_inGame2_val_start_sneak_into_the_x_18_lab_1_quest_task'), ('prior', '200'), ('storyline', 'true'),
        ('title', 'st_soc_darklab_name'), ('descr', 'st_soc_darklab_%d_descr' % i), ('target', target), ('condlist_0', cond)])

# Serega in the bandit prison: SoC val_prisoner_help
put('val_soc_prisoner_task', 'SoC val_prisoner_help: free the Duty member Serega from the bandit prison (done when the cell door is opened, fails when he dies)', [
    ('icon', 'ui_inGame2_val_start_save_the_prisoner_quest_task'), ('prior', '100'), ('storyline', 'true'),
    ('title', 'st_soc_prisoner_name'), ('descr', 'st_soc_prisoner_descr'), ('target', 'val_smart_terrain_20_duty_1_squad'),
    ('condlist_0', '{+VAL_VAL_DOOR_METAL_2_OPEN_INFO} complete'),
    ('condlist_1', '{+VAL_SMART_TERRAIN_20_DUTY_1_SQUAD_DEAD} fail')])

# code doors: SoC dar_codedoor_1 / 2, objective 1 "Discover the code", objective 2 "Open the door using the code"
for n in (1, 2):
    put('x18_soc_codedoor_%d_code_task' % n, 'SoC dar_codedoor_%d, objective 1 (done when the party holds the document with the code)' % n, [
        ('icon', 'ui_inGame2_x18_start_find_the_password_x18_codedoor_%d_task' % n), ('prior', '150'), ('storyline', 'true'),
        ('title', 'st_x18_start_find_the_password_x18_codedoor_%d_task_name' % n), ('descr', 'st_x18_start_find_the_password_x18_codedoor_%d_task_descr' % n),
        ('target', 'x18_codedoor_%d' % n), ('condlist_0', '{+X18_START_GO_TO_X18_DOC_%d_TASK_INFO} complete' % n),
        ('condlist_1', '{+X18_CODEDOOR_%d_OPEN_INFO} complete' % n)])
    put('x18_soc_codedoor_%d_open_task' % n, 'SoC dar_codedoor_%d, objective 2 "Open the door using the code"' % n, [
        ('icon', 'ui_inGame2_x18_start_find_the_password_x18_codedoor_%d_task' % n), ('prior', '150'), ('storyline', 'true'),
        ('title', 'st_soc_codedoor_%d_open_name' % n), ('descr', 'st_soc_codedoor_%d_open_descr' % n),
        ('target', 'x18_codedoor_%d' % n), ('condlist_0', '{+X18_CODEDOOR_%d_OPEN_INFO} complete' % n)])

tm = tm.replace('\n\n\n', '\n\n').rstrip('\n') + '\n'
write(tm_path, tm.replace('\n', nl).encode('cp1251'))

# ---------------------------------------------------------------------------------------------------
# 2. raid restrictor (Dark Valley side of the lab entrance)
# ---------------------------------------------------------------------------------------------------
raid = '''[logic]
active 												= sr_idle@x18_start_get_out_of_the_lab_quest_task_idle

; Original SoC: the raid (val_raid_start) begins when the X18 documents are found (bar_darklab_documents2, objective 1); the mod used to wait
; for a dead poltergeist. The tasks come from coop_soc_dv.script (every player), not from this logic.
[sr_idle@x18_start_get_out_of_the_lab_quest_task_idle]
on_info  											= {+BAR_DARKLAB_DOCUMENT_GAIN} sr_idle@x18_start_get_out_of_the_lab_quest_task_end

[sr_idle@x18_start_get_out_of_the_lab_quest_task_end]
on_any_player_inside 									= sr_idle@nil %+X18_START_GET_OUT_OF_THE_LAB_QUEST_TASK_INFO =create_squad(val_smart_terrain_17_military_1_squad:val_smart_terrain_17) =create_squad(val_smart_terrain_17_military_2_squad:val_smart_terrain_17) =create_squad(val_smart_terrain_17_military_3_squad:val_smart_terrain_17) =send_tip(st_val_monolith_trader_pda1:all_players_message_from_sidorovich) +VAL_RAID_START%

[sr_idle@nil]
'''
write(P('darkvalley_restore', 'gamedata', 'configs', 'scripts', 'coop_l04_darkvalley', 'space_restrictors',
        'x18_start_get_out_of_the_lab_quest_task_space_restrictor.ltx'), raid.replace('\n', '\r\n').encode('ascii'))

# ---------------------------------------------------------------------------------------------------
# 3. hidden tasks
# ---------------------------------------------------------------------------------------------------
HIDDEN = ['bar_start_sneak_into_the_x_18_lab_quest_task', 'val_start_go_to_the_sos_signal_1_quest_task', 'val_start_go_to_the_sos_signal_2_quest_task',
          'val_start_fake_gauss_1_quest_task', 'val_start_fake_gauss_2_quest_task', 'val_start_show_documents_to_sidorovich_quest_task',
          'x18_start_go_to_x18_doc_1_task', 'x18_start_go_to_x18_doc_2_task', 'x18_start_go_to_x18_doc_3_task',
          'x18_start_find_the_password_x18_codedoor_1_task', 'x18_start_find_the_password_x18_codedoor_2_task',
          'x18_start_kill_the_flame_poltergeist_quest_task', 'x18_start_get_out_of_the_lab_quest_task']
hp = P('repeatable_quests', 'gamedata', 'configs', 'misc', 'coop_hidden_tasks.ltx')
raw = open(hp, 'rb').read()
txt = raw.decode('cp1251')
hnl = '\r\n' if '\r\n' in txt else '\n'
marker = '; Dark Valley / X18 / Bar X18 job (patch soc_dv_x18_quests)'
if marker not in txt:
    add = [marker + ': the level maker\'s SOS, fake Gauss, document, poltergeist and exit steps and the Sidorovich document step have no SoC objective;',
           '; the SoC steps replacing them come from coop_soc_dv.script. Their sections stay in the tm_coop files (old saves).']
    add += HIDDEN
    txt = txt.rstrip('\r\n') + hnl + hnl + hnl.join(add) + hnl
    write(hp, txt.encode('cp1251'))
else:
    missing = [h for h in HIDDEN if h not in txt]
    if missing:
        txt = txt.rstrip('\r\n') + hnl + hnl.join(missing) + hnl
        write(hp, txt.encode('cp1251'))

# ---------------------------------------------------------------------------------------------------
# 4. level logic copies
# ---------------------------------------------------------------------------------------------------
def copy_edit(rel, subs):
    src = open(os.path.join(mod, 'configs', 'scripts', rel.replace('/', os.sep)), 'rb').read()
    out = src
    for pat, rep in subs:
        out, n = re.subn(pat, rep, out)
        assert n == 1, (rel, pat, n)
    write(P('soc_dv_x18_quests', 'gamedata', 'configs', 'scripts', rel.replace('/', os.sep)), out)


copy_edit('coop_l04_x18/x18_codedoor_1.ltx', [(rb'=give_task\(x18_start_find_the_password_x18_codedoor_1_task\)', b'+DAR_DOOR1_CLOSED')])
copy_edit('coop_l04_x18/x18_codedoor_2.ltx', [(rb'=give_task\(x18_start_find_the_password_x18_codedoor_2_task\)', b'+DAR_DOOR2_CLOSED')])
copy_edit('coop_l04_darkvalley/val_smart_terrain_18_walker_duty_bullet.ltx',
          [(rb'=give_task\(val_start_follow_the_bullet_quest_task\)', b'+VAL_ESCORT_TASK_START')])
bar_sr = ('[logic]\r\nactive 												= sr_idle@nil\r\n\r\n'
          '; Original logic: after the Agroprom documents a 30 s timer set BAR_SMART_TERRAIN_1_TRADER_BARMEN_AGR_DOC_INFO and, once the Barkeep had spoken\r\n'
          '; about Dark Valley, gave the level maker\'s task. In SoC the Barkeep offers the X18 job in the same talk as the hand-in (dialog\r\n'
          '; bar_soc_barmen_start_dialog) and the tasks come from coop_soc_dv.script (patch soc_dv_x18_quests).\r\n'
          '[sr_idle@nil]\r\n')
write(P('soc_dv_x18_quests', 'gamedata', 'configs', 'scripts', 'coop_l05_bar', 'space_restrictors',
        'bar_start_sneak_into_the_x_18_lab_quest_task_space_restrictor.ltx'), bar_sr.encode('ascii'))

print('changed:', changed if changed else 'nothing (already applied)')
