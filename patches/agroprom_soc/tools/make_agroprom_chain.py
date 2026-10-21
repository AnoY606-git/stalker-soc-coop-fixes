"""Makes the configs of patch agroprom_soc from the mod's own files (idempotent on the mod files).

  python make_agroprom_chain.py <mod gamedata.db0 folder> <patch gamedata folder>

Writes (everything else in these files is byte for byte the mod's):
  configs\\misc\\tm_coop_l03_agroprom.ltx              tasks of the Agroprom level, SoC objective order (see NOTES.md)
  configs\\misc\\tm_coop_l03_agroprom_underground.ltx  tasks of the Agroprom underground, one task for the stash like SoC
  configs\\misc\\squad_descr_coop_l03_agroprom.ltx     Mole's squad sets AGR_SMART_TERRAIN_4_STALKER_MOLE_SQUAD_DEAD when it dies
  configs\\scripts\\coop_l03_agroprom\\agr_smart_terrain_7_walker_alarm.ltx   the alarm stalker no longer calls give_task (it hands a task to ONE player)
The two text files (st_agroprom_soc_chain.xml, st_dialogs_coop_l03_agroprom.xml, eng + rus) come from gen_agroprom_text.py.
"""
import os
import re
import sys

mod, out = sys.argv[1], sys.argv[2]


def rd(rel):
    return open(os.path.join(mod, *rel.split('/')), 'rb').read().decode('utf-8')


def wr(rel, text):
    p = os.path.join(out, *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(text.encode('utf-8'))
    print('wrote', rel, len(text))


NL = '\r\n'


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


# ---------------------------------------------------------------------------------------------------------------------------------
# Agroprom
# ---------------------------------------------------------------------------------------------------------------------------------
MOLE_TALK = 'AGR_SMART_TERRAIN_7_STALKER_MOLE_TALK_TO_THE_STALKER_MOLE_STOP_DIALOG_INFO'
AT_WELL = 'AGR_START_FOLLOW_THE_STALKER_MOLE_QUEST_TASK_THE_AND_INFO'
MOLE_DEAD = 'AGR_SMART_TERRAIN_4_STALKER_MOLE_SQUAD_DEAD'
M1 = 'AGR_SMART_TERRAIN_5_MILITARY_1_SQUAD_DEAD'
M2 = 'AGR_SMART_TERRAIN_5_MILITARY_2_SQUAD_DEAD'

tm = rd('configs/misc/tm_coop_l03_agroprom.ltx')

# SoC agr_help_krot ("Save Mole"): given by the server tick when the Mole's PDA call starts (cat scene) or the first soldiers fall
tm = replace_section(tm, 'agr_start_save_the_stalker_mole_quest_task', [
    kv('icon', 'ui_inGame2_agr_start_save_the_stalker_mole_quest_task'),
    kv('prior', '455'),
    kv('storyline', 'true'),
    kv('title', 'st_agr_start_save_the_stalker_mole_quest_task_name'),
    kv('descr', 'st_agr_start_save_the_stalker_mole_quest_task_descr'),
    kv('target', 'agr_smart_terrain_7_stalker_mole'),
    kv('condlist_0', '{+%s +%s} complete' % (M1, M2)),
    kv('condlist_1', '{+%s} fail' % MOLE_DEAD),
    kv('condlist_2', '{+%s} complete' % MOLE_TALK),
])

# SoC agr_meet_krot_band: ONE task. "Meet Mole's group" (objective 1) until Mole waits at the well, then "Get info from Mole" (objective 2).
# Given on arrival (server tick). The old "follow Mole" step and the separate "talk" task are gone (the talk task section stays, never given).
tm = replace_section(tm, 'agr_start_follow_the_stalker_mole_quest_task', [
    kv('icon', 'ui_inGame2_agr_start_follow_the_stalker_mole_quest_task'),
    kv('prior', '465'),
    kv('storyline', 'true'),
    kv('title', 'st_agr_start_follow_the_stalker_mole_quest_task_name'),
    kv('descr', '{+%s} st_agr_start_talk_to_the_stalker_mole_quest_task_descr, st_agr_start_follow_the_stalker_mole_quest_task_descr' % AT_WELL),
    kv('target', 'agr_smart_terrain_7_stalker_mole'),
    kv('condlist_0', '{+%s} complete' % MOLE_TALK),
])

# SoC agroprom_find_gunslinger_cache objective 0 on the surface: go down (the underground task continues it)
tm = replace_section(tm, 'agr_start_go_to_the_agroprom_underground_quest_task', [
    kv('icon', 'ui_inGame2_agr_start_go_to_the_agroprom_underground_quest_task'),
    kv('prior', '450'),
    kv('storyline', 'true'),
    kv('title', 'st_agr_start_go_to_the_agroprom_underground_quest_task_name'),
    kv('descr', 'st_agr_start_go_to_the_agroprom_underground_quest_task_descr'),
    kv('target', 'agr_agru_level_changer'),
    kv('condlist_0', '{+AGR_START_GO_TO_THE_AGROPROM_UNDERGROUND_QUEST_TASK_INFO} complete'),
])

# SoC agr_help_stalkers (new): the call for help at the factory, done when the first soldier squad is dead
new_tasks = NL.join([
    '',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    ';-- Original SoC order (patch agroprom_soc, see its NOTES.md). Objectives of one SoC task are one mod task whose description and target',
    ';-- change with the story flags (descr / target condlists, evaluated per player like SoC objectives).',
    ';--   agr_soc_help_stalkers_task                    SoC agr_help_stalkers  ("Help the stalkers")',
    ';--   agr_start_save_the_stalker_mole_quest_task    SoC agr_help_krot      ("Save Mole")',
    ';--   agr_start_follow_the_stalker_mole_quest_task  SoC agr_meet_krot_band objectives 1 and 2 (meet the group, get the info)',
    ';--   agr_start_go_to_the_agroprom_underground...   SoC agroprom_find_gunslinger_cache objective 0 (the route from Mole)',
    ';-- The documents task is the Cordon one (esc_soc_military_documents_task, patch cordon): its objectives follow the flags below.',
    ';-- agr_start_talk_to_the_stalker_mole_quest_task, agr_start_break_into_a_military_base_quest_task and agr_start_the_destination_is_a_bar_quest_task',
    ';-- are no longer given by anything (they stay for old saves).',
    ';-- Every task here is given to EVERY player by the server tick of coop_scn_agroprom_soc.script.',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    '[agr_soc_help_stalkers_task]',
    kv('icon', 'ui_inGame2_agr_start_save_the_stalker_mole_quest_task'),
    kv('prior', '460'),
    kv('storyline', 'true'),
    kv('title', 'coop_soc_agr_help_stalkers_name'),
    kv('descr', 'coop_soc_agr_help_stalkers_descr'),
    kv('target', 'agr_smart_terrain_7_stalker_mole'),
    kv('condlist_0', '{+%s} complete' % M1),
    kv('condlist_1', '{+%s} complete' % M2),
    kv('condlist_2', '{+%s} complete' % MOLE_TALK),
    '',
])
assert '[agr_soc_help_stalkers_task]' not in tm
tm = tm.rstrip() + NL + NL + new_tasks.lstrip(NL)
wr('configs/misc/tm_coop_l03_agroprom.ltx', tm)

# ---------------------------------------------------------------------------------------------------------------------------------
# Underground
# ---------------------------------------------------------------------------------------------------------------------------------
FLASH = 'AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO'
FOUND = 'AGRU_SOC_STASH_FOUND'
SURF = 'AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO'
tu = rd('configs/misc/tm_coop_l03_agroprom_underground.ltx')

# SoC agroprom_find_gunslinger_cache objectives 1 (find the stash), 2 (find the information about Strelok in the stash), 3 (way out):
# one task. The stash box has a story id, so the marker is the box until the flash drive is taken; then the marker is dropped (SoC hides it).
tu = replace_section(tu, 'agru_start_find_the_shooter_hiding_place_task', [
    kv('icon', 'ui_inGame2_agru_start_find_the_shooter_hiding_place_task'),
    kv('prior', '450'),
    kv('storyline', 'true'),
    kv('title', 'st_agru_start_find_the_shooter_hiding_place_task_name'),
    kv('descr', '{+%s} st_agru_start_return_to_the_surface_task_descr, {+%s} coop_soc_agru_flash_descr, st_agru_start_find_the_shooter_hiding_place_task_descr' % (FLASH, FOUND)),
    kv('target', '{+%s} change_level_agroprom, agru_equipment_rucksack_01_case_0000' % FLASH),
    kv('condlist_0', '{+%s} complete' % SURF),
])

ghost = NL.join([
    '',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    ';-- Original SoC (patch agroprom_soc): the flash drive from the stash starts "Find out what happened to Ghost" (SoC agr_find_ghost, article',
    ';-- storyline_gunslinger_flash_info), which leads to Yantar, where Ghost lies dead in the X16 lab (patch yantar_restore sets X16_GHOST_DOCS_TAKEN).',
    ';-- agru_start_find_the_shooter_hiding_place_task now carries SoC objectives 1, 2 and 3 of agroprom_find_gunslinger_cache; the old second task',
    ';-- (agru_start_return_to_the_surface_task) is no longer given (it stays for old saves).',
    ';-- Given to EVERY player by the server tick of coop_scn_agroprom_soc.script (any level).',
    ';--------------------------------------------------------------------------------------------------------------------------------------',
    '[agr_soc_find_ghost_task]',
    kv('icon', 'ui_inGame2_agru_start_find_the_shooter_hiding_place_task'),
    kv('prior', '100'),
    kv('storyline', 'true'),
    kv('title', 'coop_soc_agr_ghost_name'),
    kv('descr', 'coop_soc_agr_ghost_descr'),
    kv('target', 'nil'),
    kv('condlist_0', '{+X16_GHOST_DOCS_TAKEN} complete'),
    kv('condlist_1', '{+YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO} complete'),
    '',
])
assert '[agr_soc_find_ghost_task]' not in tu
tu = tu.rstrip() + NL + NL + ghost.lstrip(NL)
wr('configs/misc/tm_coop_l03_agroprom_underground.ltx', tu)

# ---------------------------------------------------------------------------------------------------------------------------------
# Mole's squad: death flag (fallback when Mole is killed or removed)
# ---------------------------------------------------------------------------------------------------------------------------------
sq = rd('configs/misc/squad_descr_coop_l03_agroprom.ltx')
old = 'story_id = agr_smart_terrain_4_stalker_mole_squad'
assert sq.count(old) == 1
sq = sq.replace(old, 'on_death = %+' + MOLE_DEAD + '%' + NL + old)
wr('configs/misc/squad_descr_coop_l03_agroprom.ltx', sq)

# ---------------------------------------------------------------------------------------------------------------------------------
# Alarm stalker: no give_task (xr_effects.give_task hands the task to the first player only; the server tick gives it to everybody)
# ---------------------------------------------------------------------------------------------------------------------------------
al = rd('configs/scripts/coop_l03_agroprom/agr_smart_terrain_7_walker_alarm.ltx')
old = ' =give_task(agr_start_save_the_stalker_mole_quest_task)'
assert al.count(old) == 1
al = al.replace(old, '')
wr('configs/scripts/coop_l03_agroprom/agr_smart_terrain_7_walker_alarm.ltx', al)
