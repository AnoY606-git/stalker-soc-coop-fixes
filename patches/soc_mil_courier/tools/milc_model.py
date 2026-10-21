"""Model of patch soc_mil_courier: the Army Warehouses jobs mil_courier_job (the snitch Pavlik) and mil_freedom_rg6_task (Bulldog 6) of the
original Shadow of Chernobyl. One definition feeds gen_all.py (text, dialogs, characters, tasks, sections, PDA script), apply_shared.py,
check_milc_chain.py and the mock test.

Flags are story flags (shared, saved, synced to late joiners), all UPPER CASE (xr_logic only treats upper case names as story flags).
Positions are the ones of the SoC level.spawn / level.game of l07_military (same coordinates in the mod level); AI node and game vertex are the
nearest ones of the mod's level.ai (tools\\check_milc_chain.py --verify <coop.addon> recomputes them)."""

# ---------------------------------------------------------------------------------------------------
# flags
# ---------------------------------------------------------------------------------------------------
# courier job (SoC infos: mil_leader_quest2_start, mil_actor_in_khutor_zone, mil_courier_in_khutor_zone, mil_courier_call, mil_courier_dead,
# mil_ara_arrive, mil_ara_end, mil_ara_dead, mil_ara_leave, mil_courier_see_actor, mil_courier_khutor_leave, mil_leader_quest2_failed / _complete)
CSTART = 'MIL_SOC_COURIER_START'      # Lukash gave the job
CKHUT = 'MIL_SOC_COURIER_KHUTOR'      # a player is near the farmstead (the SoC restrictor mil_bandit_restrictor, r 45.4)
CPIN = 'MIL_SOC_COURIER_IN_KHUTOR'    # Pavlik stands in the farmstead zone (khutor_zone r 14.1)
CCALL = 'MIL_SOC_COURIER_CALL'        # Pavlik finished his radio call to the agent
CDEAD = 'MIL_SOC_COURIER_DEAD'        # Pavlik is dead
ARRIVE = 'MIL_SOC_ARA_ARRIVE'         # Ara reached the meeting point
AEND = 'MIL_SOC_ARA_END'              # the talk of Ara and Pavlik is over, Ara leaves
ADEAD = 'MIL_SOC_ARA_DEAD'            # Ara is dead
ALEAVE = 'MIL_SOC_ARA_LEAVE'          # Ara got away
CSEEN = 'MIL_SOC_COURIER_SEEN'        # a player came within 12 m of Pavlik before he left for the farmstead
CLEFT = 'MIL_SOC_COURIER_LEFT'        # Pavlik left the farmstead zone
CFAIL = 'MIL_SOC_COURIER_FAILED'
CDONE = 'MIL_SOC_COURIER_DONE'        # Lukash paid
CUE_CALL = 'MIL_SOC_CUE_CALL'         # voice cues (each client plays them once in its own voice language)
CUE_MEET = 'MIL_SOC_CUE_MEET'
CUE_AMBUSH = 'MIL_SOC_CUE_AMBUSH'
# Bulldog 6 order (SoC infos: bar_svoboda_rg6_start / mil_freedom_rg6_task, mil_freedom_cook_rg6_ask, mil_svoboda_rg6_gain, bar_svoboda_rg6_done)
RSTART = 'MIL_SOC_RG6_START'          # Voronin gave the order
RMET = 'MIL_SOC_RG6_COOK_MET'         # a player reached the Chef (SoC restrictor mil_cook_restrictor)
RASK = 'MIL_SOC_RG6_ASK'              # the drunk Chef told where the RG-6 is
RGOT = 'MIL_SOC_RG6_GOT'              # a player holds the RG-6
RDONE = 'MIL_SOC_RG6_DONE'            # Voronin got the RG-6
COOK_DIALOG = ['MIL_SOC_COOK_DIALOG_%d' % i for i in range(1, 7)]      # SoC mil_cook_dialog1..6 (the small talks)
COOK_DRINK = ['MIL_SOC_COOK_DRINK_%d' % i for i in range(1, 4)]        # SoC mil_freedom_cook_drink_1..3
COOK_RG6 = ['MIL_SOC_COOK_RG6_%d' % i for i in range(1, 5)]            # SoC mil_freedom_cook_rg6_1..4

# flags of the other patches that are read here
BP = 'MIL_SOC_BLOCKPOST_ACCEPTED'
CP = 'MIL_SMART_TERRAIN_12_1_FREEDOM_CAP_PROTECT_THE_BARRIER_DIALOG_INFO'
END = 'MIL_SOC_FREEDOM_QUESTS_END'
DONE = 'MIL_SOC_LUKASH_JOB_DONE'
LD = 'MIL_SMART_TERRAIN_16_FREEDOM_1_SQUAD_DEAD'

ALL_FLAGS = [CSTART, CKHUT, CPIN, CCALL, CDEAD, ARRIVE, AEND, ADEAD, ALEAVE, CSEEN, CLEFT, CFAIL, CDONE, CUE_CALL, CUE_MEET, CUE_AMBUSH,
             RSTART, RMET, RASK, RGOT, RDONE] + COOK_DIALOG + COOK_DRINK + COOK_RG6

# ---------------------------------------------------------------------------------------------------
# NPCs (created by the server with alife():create; sections / profiles / characters are written into the level files by apply_shared.py)
# ---------------------------------------------------------------------------------------------------
# lvid / gvid = nearest AI node of the mod level and its game vertex (check_milc_chain.py --verify recomputes them).
# Ara and the bodyguards are created 97 m west of the farmstead on their own way (point 5 of the mod's paths mil_smart_terrain_1_walker_6 / 5 / 4 _walk):
# the SoC start is 200 m away, where nothing is online while the players are at the farmstead (switch distance 150 m)
NPCS = {
    'pavlik': dict(section='mil_soc_pavlik', story='mil_soc_pavlik', community='freedom', rank='veteran', profile='mil_soc_pavlik',
                   pos=(-178.6, -16.9, 352.7), lvid=144842, gvid=1550, logic='mil_soc_pavlik.ltx',
                   soc_char='mil_Svoboda_stukach', visual='actors\\stalker_freedom\\stalker_freedom_1', icon='ui_inGame2_Freedom_2',
                   snd='characters_voice\\human_01\\freedom\\', rank_n=540, rep=58, name='mil_soc_pavlik_name', bio='mil_soc_pavlik_bio',
                   supplies=['wpn_walther', 'ammo_9x19_pbp = 1', 'wpn_wincheaster1300', 'ammo_12x76_zhekan = 1', 'device_torch']),
    'ara': dict(section='mil_soc_ara', story='mil_soc_ara', community='killer', rank='veteran', profile='mil_soc_ara',
                pos=(-273.9, -14.8, 373.8), lvid=65328, gvid=1566, logic='mil_soc_ara.ltx',
                soc_char='mil_Killer_informator', visual='actors\\stalker_merc\\stalker_merc_2', icon='ui_inGame2_merc_2',
                snd='characters_voice\\human_03\\killer\\', rank_n=904, rep=-149, name='mil_soc_ara_name', bio='mil_soc_ara_bio',
                supplies=['wpn_walther', 'ammo_9x19_pbp = 1', 'wpn_lr300', 'ammo_5.56x45_ap = 1', 'device_torch']),
    'g1': dict(section='mil_soc_ara_guard_1', story='mil_soc_ara_guard_1', community='killer', rank='veteran', profile='mil_soc_ara_guard',
               pos=(-273.9, -14.8, 375.3), lvid=65330, gvid=1566, logic='mil_soc_ara_guard_1.ltx'),
    'g2': dict(section='mil_soc_ara_guard_2', story='mil_soc_ara_guard_2', community='killer', rank='veteran', profile='mil_soc_ara_guard',
               pos=(-273.9, -14.8, 372.6), lvid=65326, gvid=1566, logic='mil_soc_ara_guard_2.ltx'),
    'g3': dict(section='mil_soc_ara_guard_3', story='mil_soc_ara_guard_3', community='killer', rank='veteran', profile='mil_soc_ara_guard',
               pos=(-275.4, -14.8, 375.3), lvid=64175, gvid=1566, logic='mil_soc_ara_guard_3.ltx'),
    'cook': dict(section='mil_soc_cook', story='mil_soc_cook', community='freedom', rank='veteran', profile='mil_soc_cook',
                 pos=(-76.6, -11.3, 27.9), lvid=236289, gvid=1317, logic='mil_soc_cook.ltx',
                 soc_char='mil_Svoboda_cook', visual='actors\\stalker_freedom\\stalker_freedom_3', icon='ui_inGame2_Freedom_2',
                 snd='characters_voice\\human_02\\freedom\\', rank_n=644, rep=84, name='mil_soc_cook_name', bio='mil_soc_cook_bio',
                 supplies=['wpn_pm', 'ammo_9x18_fmj = 1', 'wpn_wincheaster1300', 'ammo_12x76_zhekan = 1', 'device_torch', 'bread = 2', 'kolbasa = 3',
                           'conserva = 4']),
}
GUARD_CHAR = dict(profile='mil_soc_ara_guard', soc_char='mil_Killer_specnaz', visual='actors\\stalker_merc\\stalker_merc_2',
                  icon='ui_inGame2_merc_2', snd='characters_voice\\human_03\\killer\\', rank_n=740, rep=-86,
                  supplies=['wpn_walther', 'ammo_9x19_pbp = 1', 'wpn_lr300', 'ammo_5.56x45_ss190 = 1'])
RG6 = dict(section='wpn_rg-6', story='mil_soc_rg6', pos=(-274.55, -27.47, 245.41), lvid=62901, gvid=1518)

# map spots of the SoC restrictors (spheres)
KHUTOR_ZONE = (-176.4, -16.1, 378.2, 14.15)       # khutor_zone: Pavlik inside = mil_courier_in_khutor_zone
KHUTOR_ACTOR = (-179.9, -16.1, 364.8, 45.45)      # mil_bandit_restrictor: a player inside = mil_actor_in_khutor_zone
SEEN_DIST = 12.0                                  # Pavlik: on_actor_dist_le = 12
COOK_ZONE = (-76.3, -11.3, 27.9, 2.27)            # mil_cook_restrictor (the SoC map spot of the Chef disappears here)
PAVLIK_GO = (-175.9, -16.0, 381.7)                # end of the walk of Pavlik (mod path mil_smart_terrain_1_walker_8_walk)
ARA_END = (-169.4, -16.0, 386.7)                  # end of the walk of Ara (mod path mil_smart_terrain_1_walker_10_walk, last point)
ARA_FAR = (-380.7, -14.0, 398.3)                  # end of the way out (mod path mil_smart_terrain_1_walker_2_walk, last point)

# voice cues: (flag, file name, length in ms in the longer language)
CUES = [(CUE_CALL, 'mil_soc_courier_call', 8800), (CUE_MEET, 'mil_soc_courier_meet', 9000), (CUE_AMBUSH, 'mil_soc_courier_ambush', 4000)]

PAY_COURIER = 7000

# ---------------------------------------------------------------------------------------------------
# tasks (one tm_coop_l07_military.ltx section per SoC objective; texts: st_<id minus _task>_name / _descr)
# name = SoC task title, descr = SoC objective text (+ the SoC task description on the first step)
# ---------------------------------------------------------------------------------------------------
TASKS = [
    dict(id='mil_soc_courier_1_task', title='mil_courier_job', obj='mil_courier_phase1', article='mil_courier_job_descr',
         icon='ui_inGame2_mil_start_report_to_max_quest_task', prior=60, storyline='false', target='mil_soc_pavlik',
         conds=['{+%s} complete' % CKHUT, '{+%s} fail' % CFAIL]),
    dict(id='mil_soc_courier_2_task', title='mil_courier_job', obj='mil_courier_phase2', article=None,
         icon='ui_inGame2_mil_start_report_to_max_quest_task', prior=60, storyline='false', target='mil_soc_pavlik',
         conds=['{+%s} complete' % CCALL, '{+%s} fail' % CFAIL]),
    dict(id='mil_soc_courier_3_task', title='mil_courier_job', obj='mil_courier_phase3', article=None,
         icon='ui_inGame2_mil_start_kill_lukash_quest_task', prior=60, storyline='false', target='mil_soc_pavlik',
         conds=['{+%s} complete' % CDEAD, '{+%s} fail' % CFAIL]),
    dict(id='mil_soc_courier_4_task', title='mil_courier_job', obj='mil_courier_phase4', article=None,
         icon='ui_inGame2_mil_start_kill_lukash_quest_task', prior=60, storyline='false', target='mil_soc_ara',
         conds=['{+%s} complete' % ADEAD, '{+%s} fail' % CFAIL]),
    dict(id='mil_soc_courier_5_task', title='mil_courier_job', obj='mil_courier_phase5', article=None,
         icon='ui_inGame2_mil_start_report_to_max_quest_task', prior=60, storyline='false', target='mil_smart_terrain_3_freedom_lukash',
         conds=['{+%s} complete' % CDONE, '{+%s} fail' % CFAIL]),
    dict(id='mil_soc_rg6_1_task', title='mil_freedom_rg6_task', obj='mil_find_cook', article='mil_freedom_rg6_task_descr',
         icon='ui_inGame2_mil_start_talk_to_the_cap_quest_task', prior=70, storyline='false', target='mil_soc_cook',
         conds=['{+%s} complete' % RMET]),
    dict(id='mil_soc_rg6_2_task', title='mil_freedom_rg6_task', obj='mil_talk_cook', article=None,
         icon='ui_inGame2_mil_start_talk_to_the_cap_quest_task', prior=70, storyline='false', target='mil_soc_cook',
         conds=['{+%s} complete' % RASK]),
    dict(id='mil_soc_rg6_3_task', title='mil_freedom_rg6_task', obj='mil_rg6', article=None,
         icon='ui_inGame2_mil_start_kill_lukash_quest_task', prior=70, storyline='false', target='mil_soc_rg6',
         conds=['{+%s} complete' % RGOT]),
    dict(id='mil_soc_rg6_4_task', title='mil_freedom_rg6_task', obj='mil_return_to_voronin', article=None,
         icon='ui_inGame2_mil_start_report_to_max_quest_task', prior=70, storyline='false', target='bar_smart_terrain_4_duty_voronin',
         conds=['{+%s} complete' % RDONE]),
]

# ---------------------------------------------------------------------------------------------------
# dialog model. A phrase: (id, speaker, [next], [precondition fn], [give flags], [action fn], dict(has=[..], dont=[..]))
# speaker: npc | actor | hid (hidden redirect, no text). A phrase without a next ends the talk (dialogs.break_dialog is added).
# Function names are in the module coop_soc_milc.
# ---------------------------------------------------------------------------------------------------
N, A, H = 'npc', 'actor', 'hid'
MIL = 'coop_soc_mil'          # the Army Warehouses patch (phrases of its Lukash dialog keep its texts and PDA lines)
MILC = 'coop_soc_milc'


def P(pid, spk, nxt=(), pre=(), flags=(), acts=(), has=(), dont=()):
    return dict(id=pid, spk=spk, nxt=list(nxt), pre=list(pre), flags=list(flags), acts=list(acts), has=list(has), dont=list(dont))


# SoC info portion -> story flag (Cook / Voronin dialogs are converted from the SoC xml by gen_all.py with this table)
INFO = {'mil_freedom_rg6_task': RSTART, 'bar_svoboda_rg6_start': RSTART, 'mil_freedom_cook_rg6_ask': RASK, 'bar_svoboda_rg6_done': RDONE,
        'mil_svoboda_rg6_gain': RGOT}
for _i in range(1, 7):
    INFO['mil_cook_dialog%d' % _i] = COOK_DIALOG[_i - 1]
for _i in range(1, 4):
    INFO['mil_freedom_cook_drink_%d' % _i] = COOK_DRINK[_i - 1]
for _i in range(1, 5):
    INFO['mil_freedom_cook_rg6_%d' % _i] = COOK_RG6[_i - 1]

PRE_MAP = {'dialogs.dialog_allowed': None, 'dialogs_military.have_a_vodka': MILC + '.has_vodka', 'bar_dialogs.have_rg6': MILC + '.has_rg6'}
ACT_MAP = {'dialogs_military.transfer_vodka': MILC + '.take_vodka', 'bar_dialogs.give_rg6': MILC + '.take_rg6',
           'bar_dialogs.enter_to_dolg': MILC + '.give_suit'}

# Cook (SoC dialogs_military.xml): start dialog + actor dialogs
COOK_DIALOGS = ['mil_cook_common1', 'mil_cook_common2', 'mil_cook_common3', 'mil_cook_common4', 'mil_cook_common5', 'mil_cook_common6',
                'mil_cook_drink_for_rg6_1', 'mil_cook_drink_for_rg6_2', 'mil_cook_drink_for_rg6_3',
                'mil_cook_drunk_question_about_rg6_1', 'mil_cook_drunk_question_about_rg6_2', 'mil_cook_drunk_question_about_rg6_3']
COOK_START_SRC = 'mil_cook_dialog'          # phrase 0: "Come, sit down!"
# Voronin (SoC dialogs_bar.xml): the order and the hand-in
VORONIN_DIALOGS = ['bar_dolg_leader_join', 'bar_dolg_leader_quest_rg6_finish']
SUIT = 'dolg_scientific_outfit'              # SoC reward of the Bulldog 6 order (bar_dialogs.enter_to_dolg)


def new_id(src):
    """mod dialog id of a converted SoC dialog"""
    return 'mil_soc_' + src[len('mil_'):] if src.startswith('mil_') else 'mil_soc_' + src[len('bar_'):] if src.startswith('bar_') else 'mil_soc_' + src


def short(src):
    """key used in text ids: coop_soc_milc_<key>_<phrase id>"""
    for pre in ('mil_cook_', 'bar_dolg_leader_'):
        if src.startswith(pre):
            return {'mil_cook_': 'ck_', 'bar_dolg_leader_': 'vo_'}[pre] + src[len(pre):]
    return src


# Lukash (SoC mil_leader_start_dialog): the courier part. Phrases are added to / changed in the Lukash dialog of soc_mil_quests.
# (id, speaker, next, precondition, flags, actions) - the texts are SoC mil_leader_start_dialog_<id>
LUKASH_NEW = [
    P('90007', H, ['13001'], [MILC + '.lu_coffer']),
    P('90008', H, ['4001'], [MILC + '.lu_cwait']),
    P('90009', H, ['5001'], [MILC + '.lu_cpay']),
    P('90010', H, ['7001'], [MILC + '.lu_cfail']),
    P('1222', N, ['1223']),
    P('30021', N, ['1223']),
    P('1223', A, ['1300']),
    P('1300', N, ['1301', '1391']),
    P('1301', A, ['1500']),
    P('1391', A),
    P('1500', N, ['1501']),
    P('1501', A, [], [], [CSTART]),
    P('13001', N, ['13002']),
    P('13002', A, ['30021']),
    P('4001', N),
    P('5001', N, ['5002'], [], [CDONE], ['pay_courier']),
    P('5002', A, ['7003']),
    P('7001', N, ['7002']),
    P('7002', A, ['7003']),
]
# changes of existing phrases of the soc_mil_quests model: id -> dict of fields
LUKASH_CHANGE = {
    '90001': dict(pre=[MILC + '.lu_hub']),
    '90002': dict(pre=[MILC + '.lu_wait']),
    '90003': dict(pre=[MILC + '.lu_report']),
    '90004': dict(pre=[MILC + '.lu_capwait']),
    '90005': dict(pre=[MILC + '.lu_paid']),
    '90006': dict(pre=[MILC + '.lu_default']),
    '1221': dict(nxt=['1222']),
    '3002': dict(nxt=['30021']),
}
LUKASH_ROOT_EXTRA = ['90007', '90008', '90009', '90010']
LUKASH_DIALOG = 'mil_soc_lukash_dialog'
