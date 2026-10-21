"""The Army Warehouses quest model of the original SoC (patch soc_mil_quests): flags, the four NPC dialogs, the tasks.
One definition feeds gen_text.py, gen_dialogs.py (xml + the PDA archive script), check_mil_chain.py and the mock test.

Dialog phrase tuple: (id, speaker, [next ids], precondition function names, give_flag names, action function names)
speaker: 'npc' | 'actor' | 'hid' (hidden redirect, empty text). A phrase without a next ends the talk (dialogs.break_dialog is added).
Phrase ids are the ids of the original SoC dialogs (dialogs_military.xml); text id = coop_soc_mil_<key>_<phrase id>, taken from the
SoC string table (src_prefix + phrase id). Hidden redirect phrases and the mod's greeting have no SoC text."""

# ---------------------------------------------------------------------------------------------------
# flags (all story flags, shared and saved)
# ---------------------------------------------------------------------------------------------------
LK = 'MIL_SMART_TERRAIN_3_FREEDOM_LUKASH_HELP_FREEDOM_STOP_DIALOG_INFO'     # Lukash gave the Duty job (SoC mil_lukash_dolg_task)
MAXF = 'MIL_SMART_TERRAIN_15_FREEDOM_MAX_HELP_FREEDOM_STOP_DIALOG_INFO'     # reported to Max (SoC mil_max_arrive)
CP = 'MIL_SMART_TERRAIN_12_1_FREEDOM_CAP_PROTECT_THE_BARRIER_DIALOG_INFO'   # Cap gave the Barrier job (SoC mil_fblockpost_quest)
MD = 'MIL_SMART_TERRAIN_17_MONOLITH_1_SQUAD_DEAD'                           # the Monolith squad is dead (SoC mil_fblockpost_quest_complete)
SJ1 = 'MIL_SMART_TERRAIN_18_DUTY_SKULL_1_STOP_DIALOG_INFO'                  # Skull's sniper job accepted (SoC mil_sniper_get_job)
SJ2 = 'MIL_START_KILL_THE_SNIPER_ON_THE_TOWER_QUEST_TASK_INFO'
SD = 'MIL_SMART_TERRAIN_8_FREEDOM_1_SQUAD_DEAD'                             # the tower sniper is dead (SoC mil_sniper_dead)
ST = 'MIL_SMART_TERRAIN_18_DUTY_SKULL_TALK_TO_SKULL_ABOUT_THE_ASSAULT_STOP_DIALOG_INFO'   # Skull's assault talk done (SoC mil_dolg_skull_talk)
KEY = 'MIL_START_TAKE_KEY_POSITIONS_QUEST_TASK_INFO'                        # the assault job accepted (SoC mil_dolg_final_task)
LD = 'MIL_SMART_TERRAIN_16_FREEDOM_1_SQUAD_DEAD'                            # Lukash is dead (SoC mil_lukash_dead)
SKULL_DEAD = 'MIL_SMART_TERRAIN_14_DUTY_SKULL_SQUAD_DEAD'
DUTY_DEAD = ['MIL_SMART_TERRAIN_14_DUTY_SKULL_SQUAD_DEAD'] + ['MIL_SMART_TERRAIN_14_DUTY_%d_SQUAD_DEAD' % i for i in range(2, 10)]
SNIPER_DEAD = ['MIL_SMART_TERRAIN_6_FREEDOM_1_SQUAD_DEAD', 'MIL_SMART_TERRAIN_5_FREEDOM_1_SQUAD_DEAD', 'MIL_SMART_TERRAIN_4_FREEDOM_1_SQUAD_DEAD']
# new flags
DD = 'MIL_SOC_DUTY_DEAD'                    # derived: the whole Duty group is dead (SoC mil_dolg_dead)
DONE = 'MIL_SOC_LUKASH_JOB_DONE'            # Lukash heard the report (SoC mil_lukash_dolg_task_complete)
BP = 'MIL_SOC_BLOCKPOST_ACCEPTED'           # Lukash sent the player to the Barrier (SoC mil_lukash_blockpost)
END = 'MIL_SOC_FREEDOM_QUESTS_END'          # Lukash paid the Barrier job (SoC mil_freedom_quests_end)
CR = 'MIL_SOC_CAP_REWARD'                   # Cap thanked the player (SoC mil_fblockpost_quest_reward)
FEE = 'MIL_SOC_DUTY_FEE'                    # Skull paid the fee (SoC mil_dolg_gulag_free / military_scull_give_reward_2)
RADIO = 'MIL_START_GO_TO_RADAR_QUEST_TASK_INFO'     # set by the Radar level (Barkeep sent the player there)
RAD_DONE = 'RAD_START_GO_TO_RADAR_QUEST_TASK_INFO'
CAP_FAIL = 'MIL_START_TALK_TO_THE_CAP_QUEST_TASK_FAIL_INFO'

# NPC story ids (the names the task sections use as target)
NPC = {'lukash': 'mil_smart_terrain_3_freedom_lukash', 'max': 'mil_smart_terrain_15_freedom_max',
       'cap': 'mil_smart_terrain_12_1_freedom_cap', 'skull': 'mil_smart_terrain_18_duty_skull'}

# ---------------------------------------------------------------------------------------------------
# dialogs
# ---------------------------------------------------------------------------------------------------
N, A, H = 'npc', 'actor', 'hid'


def P(pid, spk, nxt=(), pre=(), flags=(), acts=()):
    return (pid, spk, list(nxt), list(pre), list(flags), list(acts))


DIALOGS = {
    # ---- Lukash (SoC mil_leader_start_dialog): the Duty job, the Barrier job, the reward ----
    'lu': dict(id='mil_soc_lukash_dialog', src='mil_leader_start_dialog_', npc='lukash', phrases=[
        P('0', H, ['90001', '90002', '90003', '90004', '90005', '90006']),
        P('90001', H, ['1001'], ['lu_st_hub']),
        P('90002', H, ['2001'], ['lu_st_wait']),
        P('90003', H, ['3001'], ['lu_st_report']),
        P('90004', H, ['9001'], ['lu_st_capwait']),
        P('90005', H, ['10001'], ['lu_st_paid']),
        P('90006', H, ['6001'], ['lu_st_default']),
        P('1001', N, ['1100', '1200', '14001', '10011']),
        P('1100', A, ['1101'], ['lu_new_alive']),
        P('1101', N, ['11011']),
        P('11011', A, ['11012'], [], [LK]),
        P('11012', N),
        P('1200', A, ['1210'], ['lu_new_dead']),
        P('1210', N, ['1221']),
        P('1221', A, ['7003'], [], [DONE]),
        P('14001', A, ['7003'], ['lu_offer']),
        P('10011', A, ['10012']),
        P('10012', N),
        P('2001', N),
        P('3001', N, ['3002']),
        P('3002', A, ['7003'], [], [DONE]),
        P('7003', N, ['7004', '7006']),
        P('7004', A, [], [], [BP]),
        P('7006', A, ['7007']),
        P('7007', N),
        P('9001', N),
        P('10001', N, [], [], [END], ['pay_member']),
        P('6001', N),
    ]),
    # ---- Max (SoC mil_max_dialog): reports ----
    'mx': dict(id='mil_soc_max_dialog', src='mil_max_dialog_', npc='max', phrases=[
        P('0', H, ['90001', '90002', '90003', '90004', '90005']),
        P('90001', H, ['2001'], ['mx_st_nojob']),
        P('90002', H, ['1001'], ['mx_st_job']),
        P('90003', H, ['9100'], ['mx_st_dd']),
        P('90004', H, ['10001'], ['mx_st_busy']),
        P('90005', H, ['31'], ['mx_st_after']),
        P('2001', N),
        P('1001', N, ['1200']),
        P('1200', A, ['1201']),
        P('1201', N, ['1210', '1220', '1100']),
        P('1210', A, ['1101']),
        P('1220', A, ['1101']),
        P('1100', A, ['1101']),
        P('1101', N, ['1102']),
        P('1102', A, [], [], [MAXF]),
        P('9100', N, ['9101']),
        P('9101', A),
        P('10001', N, ['10002']),
        P('10002', A),
        P('31', N),
    ]),
    # ---- Skull (SoC mil_dolg_skull_dialog): the sniper job, the assault, the fee ----
    'sk': dict(id='mil_soc_skull_dialog', src='mil_dolg_skull_dialog_', npc='skull', phrases=[
        P('0', H, ['90001', '90002', '90003', '90004', '90005', '90006', '90007', '90008']),
        P('90001', H, ['100'], ['sk_st_new']),
        P('90002', H, ['300'], ['sk_st_job']),
        P('90003', H, ['400'], ['sk_st_pay1']),
        P('90004', H, ['451'], ['sk_st_pay2']),
        P('90005', H, ['501'], ['sk_st_alt']),
        P('90006', H, ['601'], ['sk_st_assault']),
        P('90007', H, ['200'], ['sk_st_after']),
        P('90008', H, ['701'], ['sk_st_done']),
        P('100', N, ['101', '1001']),
        P('101', A, ['102']),
        P('102', N, ['103']),
        P('103', A, ['104']),
        P('104', N, ['105', '1041']),
        P('105', A, ['1051'], [], [SJ1, SJ2]),
        P('1051', N),
        P('1041', A, ['1042']),
        P('1042', N),
        P('1001', A, ['1002']),
        P('1002', N),
        P('300', N),
        P('400', N, ['450'], [], [], ['pay_sniper']),
        P('450', A, ['451']),
        P('451', N, ['401', '411']),
        P('401', A, ['402'], [], [ST, KEY]),
        P('402', N, ['403']),
        P('403', A),
        P('411', A, ['412'], [], [ST]),
        P('412', N, ['413']),
        P('413', A),
        P('501', N, ['502']),
        P('502', A, ['503'], [], [SJ1, SJ2]),
        P('503', N, ['504'], [], [], ['pay_sniper']),
        P('504', A, ['451']),
        P('601', N),
        P('200', N, ['201']),
        P('201', A, [], [], [FEE], ['pay_fee']),
        P('701', N),
    ]),
    # ---- Cap (SoC mil_freedom_commander): the Barrier job and its reward ----
    'cp': dict(id='mil_soc_cap_dialog', src='mil_freedom_commander_', npc='cap', phrases=[
        P('0', H, ['90001', '90002', '90003', '90004']),
        P('90001', H, ['4003'], ['cp_st_new']),
        P('90002', H, ['2001'], ['cp_st_wait']),
        P('90003', H, ['3001'], ['cp_st_reward']),
        P('90004', H, ['3003'], ['cp_st_done']),
        P('4003', N, ['1004']),
        P('1004', A, ['1005'], [], [CP]),
        P('1005', N),
        P('2001', N),
        P('3001', N, ['3002']),
        P('3002', A, ['3003'], [], [CR], ['pay_cap']),
        P('3003', N),
    ]),
    # ---- Cap lore (SoC mil_freedom_commander_common2): "What's this place?", an actor dialog without conditions ----
    'cl': dict(id='mil_soc_cap_lore_dialog', src='mil_freedom_commander_common2_', npc='cap', phrases=[
        P('0', A, ['1']), P('1', N, ['2']), P('2', A, ['3']), P('3', N, ['4']), P('4', A, ['5']), P('5', N, ['6']), P('6', A, ['7']), P('7', N),
    ], plain=True),
}

# the mod's own greeting of Max (state "after": nothing to do, the flash drive dialogs follow as actor dialogs)
MAX_GREETING = 'mil_smart_terrain_15_freedom_max_start_dialog_0'

# the mod dialogs that these replace (removed from dialogs_coop_l07_military.xml and from the character descriptions)
REMOVED_DIALOGS = [
    'mil_smart_terrain_18_duty_skull_start_dialog', 'mil_smart_terrain_18_duty_skull_kill_freedom_sniper_start_dialog',
    'mil_smart_terrain_18_duty_skull_talk_to_skull_about_the_assault_start_dialog',
    'mil_smart_terrain_3_freedom_lukash_start_dialog', 'mil_smart_terrain_3_freedom_lukash_no_problem_start_dialog',
    'mil_smart_terrain_3_freedom_lukash_help_freedom_start_dialog',
    'mil_smart_terrain_15_freedom_max_start_dialog', 'mil_smart_terrain_15_freedom_max_help_freedom_start_dialog',
    'mil_smart_terrain_12_1_freedom_cap_start_dialog', 'mil_smart_terrain_12_1_freedom_cap_protect_the_barrier_dialog',
]
# character -> (new start dialog, extra actor dialogs added after the removed ones)
CHARACTERS = {
    'mil_smart_terrain_3_freedom_lukash': ('mil_soc_lukash_dialog', []),
    'mil_smart_terrain_15_freedom_max': ('mil_soc_max_dialog', []),
    'mil_smart_terrain_18_duty_skull': ('mil_soc_skull_dialog', []),
    'mil_smart_terrain_12_1_freedom_cap': ('mil_soc_cap_dialog', ['mil_soc_cap_lore_dialog']),
}

# ---------------------------------------------------------------------------------------------------
# tasks: new sections of tm_coop_l07_military.ltx (id, icon, target, condlist, name src, descr src)
# ---------------------------------------------------------------------------------------------------
NEW_TASKS = [
    # SoC mil_lukash_job objective "Return to Lukash"
    dict(id='mil_soc_return_lukash_task', icon='ui_inGame2_mil_start_report_to_max_quest_task', prior=50, storyline='false',
         target='mil_smart_terrain_3_freedom_lukash', cond='{+%s} complete' % DONE, name='mil_lukash_job', descr='mil_return_lukash'),
    # SoC mil_blockpost_job objective 3 "Talk to Barrier outpost commander" (the reward step)
    dict(id='mil_soc_cap_reward_task', icon='ui_inGame2_mil_start_talk_to_the_cap_quest_task', prior=150, storyline='true',
         target='mil_smart_terrain_12_1_freedom_cap', cond='{+%s} complete' % CR, name='mil_blockpost_job', descr='mil_fblockpost_phase3'),
    # SoC mil_kill_lukash objective 5 "Return to the Duty farmstead and receive my fee"
    dict(id='mil_soc_duty_fee_task', icon='ui_inGame2_mil_start_kill_lukash_quest_task', prior=50, storyline='false',
         target='mil_smart_terrain_18_duty_skull', cond='{+%s} complete' % FEE, name='mil_kill_lukash', descr='mil_dolg_return_to_khutor'),
]

# mod-only tasks that are never given any more (coop_hidden_tasks.ltx)
HIDDEN = ['mil_start_go_to_radar_quest_task', 'mil_start_kill_the_snipers_4_quest_task'] + \
         ['mil_start_kill_the_duty_%d_quest_task' % i for i in range(1, 9)]
