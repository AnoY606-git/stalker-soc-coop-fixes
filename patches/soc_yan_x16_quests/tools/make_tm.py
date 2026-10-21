"""Makes the task files of patch soc_yan_x16_quests from the mod's own files (idempotent on the mod files).

  python make_tm.py <mod gamedata.db0 folder> <patch gamedata folder>

Writes (everything else in these files is byte for byte the mod's):
  configs\\misc\\tm_coop_l08_yantar.ltx   SoC tasks of Yantar (see NOTES.md for the table old -> new)
  configs\\misc\\tm_coop_l08_x16.ltx      SoC tasks of the lab
The logic copies (Sakharov walker, helmet restrictor, ...) come from make_logic.py, the texts from gen_text.py.

Objectives of one SoC task are ONE mod task here: its description and map target are condlists over the story flags
(`descr = {+FLAG} id, id`, evaluated per player like SoC objectives, same syntax as patch agroprom_soc).
"""
import os
import re
import sys

mod, out = sys.argv[1], sys.argv[2]

NL = '\r\n'


def rd(rel):
    return open(os.path.join(mod, *rel.split('/')), 'rb').read().decode('utf-8')


def wr(rel, text):
    p = os.path.join(out, *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(text.encode('utf-8'))
    print('wrote', rel, len(text))


def sec_span(text, name):
    m = re.search(r'(?m)^\[' + re.escape(name) + r'\]\r?\n', text)
    assert m, 'section ' + name
    end = m.end()
    while end < len(text):
        nl = text.find('\n', end)
        line = text[end:nl if nl >= 0 else len(text)].strip()
        if line == '' or line.startswith('[') or line.startswith(';'):
            break
        end = nl + 1 if nl >= 0 else len(text)
    return m.start(), end


def replace_section(text, name, body):
    a, b = sec_span(text, name)
    return text[:a] + '[' + name + ']' + NL + NL.join(body) + NL + text[b:]


def kv(k, v):
    return k.ljust(12) + '= ' + v


# ------------------------------------------------------------------------------------------------------------------------------
# story flags (names of the mod; see coop_soc_yan.script, section F)
# ------------------------------------------------------------------------------------------------------------------------------
OFFERED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO'
PREP = 'YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO'
M1, M2, M3 = ('YAN_START_TAKE_MEASUREMENTS_%d_QUEST_TASK_INFO' % i for i in (1, 2, 3))
REPORTED = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO'
HELMET = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO'
LAB = 'YAN_YAN_START_INFILTRATE_THE_X16_LAB_QUEST_TASK_INFO'
VAS = 'YAN_SOC_VASILYEV_FOUND'
INSTALL = 'X16_START_FIND_THE_INSTALLATION_QUEST_TASK_INFO'
SW1, SW2, SW3, SW4 = ('X16_LAB_PRIMARY_SWITCHER_%d_DEACTIVATE_INFO' % i for i in (1, 2, 3, 4))
DOCS = 'X16_GHOST_DOCS_TAKEN'
EXIT = 'X16_START_GET_OUT_OF_THE_LAB_TASK_INFO'
DONE = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO'
GUIDE = 'YAN_SOC_GUIDE_MET'

# ------------------------------------------------------------------------------------------------------------------------------
# Yantar
# ------------------------------------------------------------------------------------------------------------------------------
ty = rd('configs/misc/tm_coop_l08_yantar.ltx')

# SoC bar_x16_documents is ONE task in patch bar_soc_quests (bar_start_go_to_yantar_quest_task): it follows YAN_X16_DOCUMENTS_GAIN and the
# Sakharov offer flag. The Yantar copy yan_start_go_to_yantar_quest_task stays untouched and is never given (coop_hidden_tasks.ltx).

# SoC yan_find_scientist: ONE task. 1 talk to Kruglov, 2 escort Kruglov to the measurement sites (the marker walks over the sites that are
# not done), 3 bring the results to Sakharov. Done by Sakharov's dialog (SoC yan_find_scientist_done).
ty = replace_section(ty, 'yan_start_talk_to_the_kruglov_quest_task', [
    kv('icon', 'ui_inGame2_yan_start_talk_to_the_kruglov_quest_task'),
    kv('prior', '200'),
    kv('storyline', 'true'),
    kv('title', 'st_yan_start_talk_to_the_kruglov_quest_task_name'),
    kv('descr', '{+%s +%s +%s} st_yan_start_talk_to_the_saharov_quest_task_descr, {+%s} st_yan_start_take_measurements_1_quest_task_descr, '
                'st_yan_start_talk_to_the_kruglov_quest_task_descr' % (M1, M2, M3, PREP)),
    kv('target', '{+%s +%s +%s} yan_smart_terrain_1_ecolog_saharov, {+%s -%s} yan_start_take_measurements_1_space_restrictor, '
                 '{+%s -%s} yan_start_take_measurements_2_space_restrictor, {+%s -%s} yan_start_take_measurements_3_space_restrictor, '
                 'yan_smart_terrain_1_ecolog_kruglov' % (M1, M2, M3, PREP, M1, PREP, M2, PREP, M3)),
    kv('condlist_0', '{+%s} complete' % REPORTED),
])

# SoC yan_find_vasilyev_task: 1 search Vasiliev's corpse (his PDA names the lab), 2 get inside the lab. The helmet comes from Sakharov's dialog.
ty = replace_section(ty, 'yan_start_infiltrate_the_x16_lab_quest_task', [
    kv('icon', 'ui_inGame2_yan_start_infiltrate_the_x16_lab_quest_task'),
    kv('prior', '200'),
    kv('storyline', 'true'),
    kv('title', 'st_yan_start_infiltrate_the_x16_lab_quest_task_name'),
    kv('descr', '{+%s} st_yan_start_infiltrate_the_x16_lab_quest_task_descr, coop_soc_yan_vasilyev_descr' % VAS),
    kv('target', '{+%s} yan_x16_level_changer, yan_vasilyev' % VAS),
    kv('condlist_0', '{+%s} complete' % LAB),
])

# SoC pays nothing for these two steps (the lab exit, the Barkeep's Radar job): the level maker's money rewards are removed
for _name in ('yan_start_talk_to_the_saharov_x16_lab_quest_task', 'yan_start_talk_to_the_barmen_quest_task'):
    _a, _b = sec_span(ty, _name)
    _sec = ty[_a:_b]
    _new = re.sub(r'(?m)^reward_money.*(?:\r?\n|$)', '', _sec)
    assert _new != _sec, _name
    ty = ty[:_a] + _new + ty[_b:]

new = NL.join([
    '',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    ';-- Original SoC order (patch soc_yan_x16_quests, see its NOTES.md). Objectives of one SoC task are one mod task whose description and',
    ';-- target change with the story flags. Every task is given to EVERY player by the server tick of coop_soc_yan.script.',
    ';--   bar_start_go_to_yantar_quest_task (patch bar_soc_quests) is SoC bar_x16_documents; yan_start_go_to_yantar_quest_task is never given',
    ';--   yan_soc_job_task                              SoC yan_scientist_job ("Help for the scientists")',
    ';--   yan_start_talk_to_the_kruglov_quest_task      SoC yan_find_scientist (measurements, one escort task)',
    ';--   yan_start_infiltrate_the_x16_lab_quest_task   SoC yan_find_vasilyev_task',
    ';--   yan_soc_ghost_task                            SoC yan_find_ghost_task (lab level)',
    ';--   yan_soc_guide_task                            SoC yan_provodnik_task ("Meet the Guide")',
    ';-- Never given any more (they stay for old saves and are in coop_hidden_tasks.ltx): yan_start_take_measurements_1..3_quest_task,',
    ';-- yan_start_talk_to_the_saharov_quest_task, yan_start_configuring_helmets_quest_task (mod only, SoC has no such step),',
    ';-- yan_start_talk_to_the_saharov_x16_lab_quest_task (now the last objective of x16_start_get_out_of_the_lab_task).',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    '[yan_soc_job_task]',
    kv('icon', 'ui_inGame2_yan_start_talk_to_the_saharov_quest_task'),
    kv('prior', '190'),
    kv('storyline', 'true'),
    kv('title', 'coop_soc_yan_job_name'),
    kv('descr', 'coop_soc_yan_job_descr'),
    kv('target', 'yan_smart_terrain_1_ecolog_saharov'),
    kv('condlist_0', '{+%s} complete' % HELMET),
    '',
    '[yan_soc_ghost_task]',
    kv('icon', 'ui_inGame2_yan_start_infiltrate_the_x16_lab_quest_task'),
    kv('prior', '180'),
    kv('storyline', 'true'),
    kv('title', 'coop_soc_yan_ghost_name'),
    kv('descr', '{+%s} coop_soc_yan_ghost_2_descr, coop_soc_yan_ghost_1_descr' % INSTALL),
    kv('target', '{+%s} x16_stalker_ghost, x16_yan_1_level_changer' % INSTALL),
    kv('condlist_0', '{+%s} complete' % DOCS),
    '',
    '[yan_soc_guide_task]',
    kv('icon', 'ui_inGame2_agru_start_find_the_shooter_hiding_place_task'),
    kv('prior', '170'),
    kv('storyline', 'true'),
    kv('title', 'coop_soc_yan_guide_name'),
    kv('descr', 'coop_soc_yan_guide_descr'),
    kv('target', 'esc_smart_terrain_1_stalker_guide'),
    kv('condlist_0', '{+%s} complete' % GUIDE),
    '',
])
assert '[yan_soc_job_task]' not in ty
ty = ty.rstrip() + NL + NL + new.lstrip(NL)
wr('configs/misc/tm_coop_l08_yantar.ltx', ty)

# ------------------------------------------------------------------------------------------------------------------------------
# X16 lab
# ------------------------------------------------------------------------------------------------------------------------------
tx = rd('configs/misc/tm_coop_l08_x16.ltx')

# SoC yan_kill_brain_task: the briefing, then the three control modules, then the mechanism (the primary switch). One task.
tx = replace_section(tx, 'x16_start_find_the_installation_quest_task', [
    kv('icon', 'ui_inGame2_x16_start_find_the_installation_quest_task'),
    kv('prior', '150'),
    kv('storyline', 'true'),
    kv('title', 'st_x16_start_find_the_installation_quest_task_name'),
    kv('descr', '{+%s +%s +%s} st_x16_start_turn_off_the_switch_4_task_descr, {+%s -%s} st_x16_start_turn_off_the_switch_1_task_descr, '
                '{+%s -%s} st_x16_start_turn_off_the_switch_2_task_descr, {+%s -%s} st_x16_start_turn_off_the_switch_3_task_descr, '
                'st_x16_start_find_the_installation_quest_task_descr' % (SW1, SW2, SW3, INSTALL, SW1, INSTALL, SW2, INSTALL, SW3)),
    kv('target', '{+%s +%s +%s} x16_lab_primary_switcher_4, {-%s} x16_lab_primary_switcher_1, {-%s} x16_lab_primary_switcher_2, '
                 '{-%s} x16_lab_primary_switcher_3, x16_lab_primary_switcher_4' % (SW1, SW2, SW3, SW1, SW2, SW3)),
    kv('condlist_0', '{+%s +%s +%s +%s} complete' % (SW1, SW2, SW3, SW4)),
])

# SoC yan_kill_brain_task_2: get out via the secret tunnel, talk to Sakharov (the dialog gives the done flag). One task.
tx = replace_section(tx, 'x16_start_get_out_of_the_lab_task', [
    kv('icon', 'ui_inGame2_x16_start_get_out_of_the_lab_task'),
    kv('prior', '150'),
    kv('storyline', 'true'),
    kv('title', 'st_x16_start_get_out_of_the_lab_task_name'),
    kv('descr', '{+%s} st_yan_start_talk_to_the_saharov_x16_lab_quest_task_descr, coop_soc_yan_tunnel_descr' % EXIT),
    kv('target', '{+%s} yan_smart_terrain_1_ecolog_saharov, x16_yan_2_level_changer' % EXIT),
    kv('condlist_0', '{+%s} complete' % DONE),
])

# the three level-maker module tasks are replaced by the single task above (they stay for old saves, never given)
tx = tx.rstrip() + NL + NL + NL.join([
    ';-- Patch soc_yan_x16_quests: x16_start_find_the_installation_quest_task is SoC yan_kill_brain_task (modules 1 to 3 and the mechanism) and',
    ';-- x16_start_get_out_of_the_lab_task is SoC yan_kill_brain_task_2 (secret tunnel, talk to Sakharov). x16_start_turn_off_the_switch_1..4_task',
    ';-- are no longer given (coop_hidden_tasks.ltx). Given to every player by coop_soc_yan.script.',
    ''])
wr('configs/misc/tm_coop_l08_x16.ltx', tx)
