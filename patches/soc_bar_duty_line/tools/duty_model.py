"""The Bar Duty / Freedom line of the original Shadow of Chernobyl (patch soc_bar_duty_line): flags, dialogs, tasks, NPCs, items.
One definition feeds gen_text.py, gen_dialogs.py (xml + the PDA archive script), make_tm.py, check_duty_chain.py and the mock test.

Dialog phrase tuple: (id, speaker, [next ids], precondition function names, give_flag names, action function names)
speaker: 'npc' | 'actor' | 'hid' (hidden redirect, empty text). A phrase without a next ends the talk (dialogs.break_dialog is added).
Phrase ids are the ids of the original SoC dialogs (dialogs_bar.xml); text id = coop_soc_duty_<key>_<phrase id>. The text comes from the SoC
string table (src + phrase id) or, where the retail SoC has none (cut content, see NOTES.md), from AUTH (English + Russian written for this patch)."""

# ---------------------------------------------------------------------------------------------------
# flags (all story flags, shared and saved). SoC info portions keep their name in upper case.
# ---------------------------------------------------------------------------------------------------
PASS = 'BAR_DOLG_BASE_PASS'                      # the pass at the Duty gate is bought (SoC bar_dolg_base_pass)
CSTART = 'BAR_DOLG_COMMUNITY_START'              # Join Duty started (SoC bar_dolg_community_start)
CLEAD = 'BAR_DOLG_COMMUNITY_LEADER'              # SoC bar_dolg_community_leader
TSTART = 'BAR_DOLG_VETERAN_START'                # Ivantsov's test accepted (SoC bar_dolg_veteran_start: task bar_dolg_test_quest)
ARENA = 'BAR_ARENA_PSEUDODOG_DEFEATED'           # the pseudodog fight on the Arena is won (SoC bar_arena_pseudodog_defeated)
TDONE = 'BAR_DOLG_VETERAN_DONE'                  # reported to Ivantsov (SoC bar_dolg_veteran_done)
RSTART = 'BAR_SVOBODA_RG6_START'                 # Voronin's Bulldog 6 job accepted (SoC bar_svoboda_rg6_start)
RGAIN = 'MIL_SVOBODA_RG6_GAIN'                   # a player holds the Bulldog 6 (SoC mil_svoboda_rg6_gain)
RDONE = 'BAR_SVOBODA_RG6_DONE'                   # the Bulldog 6 is handed to Voronin (SoC bar_svoboda_rg6_done)
OATH = 'BAR_DOLG_COMMUNITY_LEADER_DONE'          # the oath is sworn (SoC bar_dolg_community_leader_done)
KSTART = 'BAR_KILL_SVOBODA_LEADER_START'         # Voronin ordered the Freedom leader's death (SoC bar_kill_svoboda_leader_start)
KKILLED = 'MIL_KILL_SVOBODA_LEADER_KILLED'       # Lukash is dead (SoC mil_kill_svoboda_leader_killed)
KDONE = 'BAR_KILL_SVOBODA_LEADER_DONE'           # Voronin heard it (SoC bar_kill_svoboda_leader_done)
VSTART = 'BAR_KILL_VETERAN_START'                # Barkeep's veterans job accepted (SoC bar_kill_veteran_start)
VKILLED = 'BAR_KILL_VETERAN_KILLED'              # Lucky is dead (SoC bar_kill_veteran_killed)
VDONE = 'BAR_KILL_VETERAN_DONE'                  # Lucky's PDA handed to the Barkeep (SoC bar_kill_veteran_done)
ASTART = 'BAR_KILL_SVOBODA_AMBUSH_START'         # Barkeep's Tyran job accepted (SoC bar_kill_svoboda_ambush_start)
AKILLED = 'BAR_KILL_SVOBODA_AMBUSH_KILLED'       # Tyran is dead (SoC bar_kill_svoboda_ambush_killed)
ADONE = 'BAR_KILL_SVOBODA_AMBUSH_DONE'           # Tyran's PDA handed to the Barkeep (SoC bar_kill_svoboda_ambush_done)
# bookkeeping (new)
LPDA = 'SOC_DUTY_LUCKY_PDA_MADE'
TPDA = 'SOC_DUTY_TIRAN_PDA_MADE'
RMADE = 'SOC_DUTY_RG6_MADE'
# read from other patches / the mod
AGR_DONE = 'BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO'   # soc_dv_x18_quests: Agroprom documents handed in (SoC agroprom_military_case_done)
LUKASH_DEAD = 'MIL_SMART_TERRAIN_16_FREEDOM_1_SQUAD_DEAD'                                # soc_mil_quests / the mod: Lukash is dead

# prices (SoC bar_dialogs: has_dolg_deposite / give_dolg_deposite 1000). Rewards of the Barkeep jobs: the SoC functions are missing
# in the retail scripts, these sums are this patch's
DEPOSIT = 1000
PAY_LUCKY = 5000
PAY_TYRAN = 8000

# story ids (the names the task sections use as target)
NPC = dict(barkeep='bar_smart_terrain_1_stalker_barmen', voronin='bar_smart_terrain_4_duty_voronin', petrenko='bar_smart_terrain_4_duty_petrenko',
           arny='bar_smart_terrain_2_stalker_arny', lukash='mil_smart_terrain_3_freedom_lukash',
           commander='bar_dolg_guard_commander', ivancov='bar_dolg_captain_ivancov', lucky='bar_crazy_veterans_leader', tyran='bar_svoboda_ambush_tiran')
RG6_STORY = 'Mil_RG6'

# ---------------------------------------------------------------------------------------------------
# dialogs
# ---------------------------------------------------------------------------------------------------
N, A, H = 'npc', 'actor', 'hid'


def P(pid, spk, nxt=(), pre=(), flags=(), acts=()):
    return (pid, spk, list(nxt), list(pre), list(flags), list(acts))


DIALOGS = {
    # ---- Voronin (SoC bar_dolg_leader_start): the greeting follows the state of the Duty line ----
    'vo': dict(id='bar_soc_vo_dialog', src='bar_dolg_leader_start_', npc='voronin', phrases=[
        P('0', H, ['90001', '90002', '90003', '90004', '90005', '90006', '90007', '90008']),
        P('90001', H, ['811'], ['vo_st_kdone']),
        P('90002', H, ['81'], ['vo_st_kkilled']),
        P('90003', H, ['51'], ['vo_st_kwait']),
        P('90004', H, ['51'], ['vo_st_koffer']),
        P('90005', H, ['21'], ['vo_st_member']),
        P('90006', H, ['41'], ['vo_st_oath']),
        P('90007', H, ['31'], ['vo_st_rg6']),
        P('90008', H, ['11'], ['vo_st_hub']),
        P('811', N),                                         # same text as 81 (SoC [8]/[81]: "You killed the leader"), the talk is over, nothing to give
        P('81', N, [], [], [KDONE]),
        P('51', N, [], [], [KSTART]),
        P('21', N), P('41', N), P('11', N),
        P('31', N, ['311']),
        P('311', A, ['3111'], [], [RDONE], ['take_rg6']),
        P('3111', N, [], [], [], ['give_outfit']),
    ]),
    # ---- Voronin: the job of the Bulldog 6 (SoC bar_dolg_leader_join), an actor dialog ----
    'vj': dict(id='bar_soc_vj_dialog', src='bar_dolg_leader_join_', npc='voronin', pre='vj_ok', phrases=[
        P('0', A, ['1']),
        P('1', N, ['11']),
        P('11', A, ['111']),
        P('111', N, ['1111', '1112']),
        P('1111', A, ['11111'], [], [RSTART]),
        P('11111', N),
        P('1112', A, ['11121']),
        P('11121', N),
    ]),
    # ---- Voronin: the oath (SoC bar_dolg_leader_prisyaga) ----
    'vp': dict(id='bar_soc_vp_dialog', src='bar_dolg_leader_prisyaga_', npc='voronin', pre='vp_ok', phrases=[
        P('0', A, ['1']), P('1', N, ['2']), P('2', A, ['3']), P('3', N, ['4']), P('4', A, ['5']), P('5', N, ['6']), P('6', A, ['7']),
        P('7', N, ['8']),
        P('8', A, ['9'], [], [OATH], ['set_dolg']),
        P('9', N),
    ]),
    # ---- Voronin: the hand-in as an actor dialog (SoC bar_dolg_leader_quest_rg6_finish) ----
    'vr': dict(id='bar_soc_vr_dialog', src='bar_dolg_leader_quest_rg6_finish_', npc='voronin', pre='vr_ok', phrases=[
        P('0', A, ['1'], [], [RDONE], ['take_rg6']),
        P('1', N, [], [], [], ['give_outfit']),
    ]),
    # ---- Voronin: "What can I do for Duty?" (SoC bar_dolg_leader_job) ----
    'vb': dict(id='bar_soc_vb_dialog', src='bar_dolg_leader_job_', npc='voronin', pre='vb_ok', phrases=[
        P('0', A, ['1']), P('1', N),
    ]),
    # ---- Petrenko (SoC bar_dolg_petrenko_start) ----
    'pe': dict(id='bar_soc_pe_dialog', src='bar_dolg_petrenko_start_', npc='petrenko', phrases=[
        P('0', H, ['90001', '90002', '90003']),
        P('90001', H, ['31'], ['gc_st_member']),
        P('90002', H, ['21'], ['gc_st_pass']),
        P('90003', H, ['11'], ['gc_st_default']),
        P('31', N), P('21', N), P('11', N),
    ]),
    # ---- Gate commander (SoC bar_dolg_base_guard_start) ----
    'gc': dict(id='bar_soc_gc_dialog', src='bar_dolg_base_guard_start_', npc='commander', phrases=[
        P('0', H, ['90001', '90002', '90003']),
        P('90001', H, ['31'], ['gc_st_member']),
        P('90002', H, ['21'], ['gc_st_pass']),
        P('90003', H, ['11'], ['gc_st_default']),
        P('31', N), P('21', N), P('11', N),
    ]),
    # ---- Gate commander: "Why don't you let outsiders in?" (SoC bar_dolg_base_guard_talk) ----
    'gt': dict(id='bar_soc_gt_dialog', src='bar_dolg_base_guard_talk_', npc='commander', phrases=[
        P('0', A, ['1']), P('1', N, ['2']), P('2', A, ['3']), P('3', N),
    ], plain=True),
    # ---- Gate commander: the pass for 1000 (SoC bar_dolg_base_guard_acces) ----
    'ga': dict(id='bar_soc_ga_dialog', src='bar_dolg_base_guard_acces_', npc='commander', pre='ga_ok', phrases=[
        P('0', A, ['1']),
        P('1', N, ['11', '12']),
        P('11', A, ['111'], ['has_deposit'], [PASS, CSTART, CLEAD], ['take_deposit']),
        P('111', N),
        P('12', A, ['121']),
        P('121', N),
    ]),
    # ---- Ivantsov (SoC bar_dolg_ivancov_start; the test offer and the report are this patch's, the retail SoC has no dialog for the task) ----
    'iv': dict(id='bar_soc_iv_dialog', src='bar_dolg_ivancov_start_', npc='ivancov', phrases=[
        P('0', H, ['90001', '90002', '90003']),
        P('90001', H, ['31'], ['gc_st_member']),
        P('90002', H, ['21'], ['gc_st_pass']),
        P('90003', H, ['11'], ['gc_st_default']),
        P('31', N), P('11', N),
        P('21', N, ['I1', 'I5']),
        P('I1', A, ['I2'], ['iv_offer']),
        P('I2', N, ['I3']),
        P('I3', A, [], [], [TSTART]),
        P('I5', A, ['I6'], ['iv_report'], [TDONE]),
        P('I6', N),
    ]),
    # ---- Barkeep: "You got any special jobs?" (SoC bar_bar_barmen_jobs, the two Duty jobs) ----
    'bj': dict(id='bar_soc_bj_dialog', src='bar_bar_barmen_jobs_', npc='barkeep', pre='bj_ok', phrases=[
        P('0', A, ['90001', '90002', '90003', '90004']),
        P('90001', H, ['321'], ['bj_vet_offer']),
        P('90002', H, ['271'], ['bj_vet_busy']),
        P('90003', H, ['331'], ['bj_amb_offer']),
        P('90004', H, ['311'], ['bj_none']),
        P('321', N, ['3211']),
        P('3211', A, ['32111']),
        P('32111', N, ['32112', '32113']),
        P('32112', A, ['321121'], [], [VSTART]),
        P('321121', N),
        P('32113', A, ['321131']),
        P('321131', N),
        P('271', N),
        P('331', N, ['3312', '3313']),
        P('3312', A, ['33121'], [], [ASTART]),
        P('33121', N),
        P('3313', A, ['33131']),
        P('33131', N),
        P('311', N),
    ]),
    # ---- Barkeep: Lucky's PDA (SoC bar_bar_barman_veterans_finish) ----
    'bv': dict(id='bar_soc_bv_dialog', src='bar_bar_barman_veterans_finish_', npc='barkeep', pre='bv_ok', phrases=[
        P('0', A, ['1']),
        P('1', N, ['11']),
        P('11', A, ['111'], [], [VDONE], ['take_lucky_pda', 'pay_lucky']),
        P('111', N),
    ]),
    # ---- Barkeep: Tyran's PDA (SoC bar_bar_barman_killer_ambush) ----
    'ba': dict(id='bar_soc_ba_dialog', src='bar_bar_barman_killer_ambush_', npc='barkeep', pre='ba_ok', phrases=[
        P('0', A, ['1']),
        P('1', N, ['2']),
        P('2', A, ['3'], [], [ADONE], ['take_tyran_pda', 'pay_tyran']),
        P('3', N),
    ]),
}

# the characters and the dialogs they start with (new characters are in character_desc_coop_soc_duty.xml; the first three exist in the mod
# and are changed by tools\apply_shared.py): character -> (start dialog, [actor dialogs])
SHARED_CHARACTERS = {
    'bar_smart_terrain_4_duty_voronin': ('bar_soc_vo_dialog', ['bar_soc_vj_dialog', 'bar_soc_vp_dialog', 'bar_soc_vr_dialog', 'bar_soc_vb_dialog']),
    'bar_smart_terrain_4_duty_petrenko': ('bar_soc_pe_dialog', []),
    'bar_smart_terrain_1_stalker_barmen': (None, ['bar_soc_bj_dialog', 'bar_soc_bv_dialog', 'bar_soc_ba_dialog']),
}
NEW_DIALOG_CHARS = {
    'bar_dolg_guard_commander': ('bar_soc_gc_dialog', ['bar_soc_gt_dialog', 'bar_soc_ga_dialog']),
    'bar_dolg_ivancov': ('bar_soc_iv_dialog', []),
}

# texts the retail SoC does not have (cut content): id suffix -> (English, Russian). Task and item texts use the same table.
AUTH = {
    'iv_I1': ("I bought a pass at the gate. What do I have to do to join Duty?", u"Я купил пропуск у ворот. Что нужно сделать, чтобы вступить в Долг?"),
    'iv_I2': ("Before we get to the conclusions, pass an easy test. Win a fight against the pseudodog on the Arena, then come back to me. "
              "When that is done we'll decide whether you're fit to join Duty or not.",
              u"Прежде чем мы перейдём к выводам, пройди несложную проверку. Победи псевдособаку на Арене и возвращайся ко мне. "
              u"Когда это будет сделано, мы решим, годишься ли ты для Долга."),
    'iv_I3': ("Understood.", u"Понял."),
    'iv_I5': ("I won on the Arena.", u"Я победил на Арене."),
    'iv_I6': ("Not bad. Go see Voronin in the bunker, he decides the rest.", u"Неплохо. Иди к Воронину в бункер, остальное решает он."),
    # tasks
    'task_test_name': ("Prove yourself to Captain Ivantsov", u"Докажи свою пригодность капитану Иванцову"),
    'task_test_win': ("Win a fight against the pseudodog on the Arena", u"Победить псевдособаку на Арене"),
    'task_test_back': ("Return to Captain Ivantsov", u"Вернуться к капитану Иванцову"),
    'task_leader_name': ("Kill the leader of Freedom", u"Убить лидера Свободы"),
    'task_leader_kill': ("Kill the leader of Freedom, Lukash, in the Army Warehouses", u"Убить лидера Свободы, Лукаша, на Армейских складах"),
    'task_leader_back': ("Report to General Voronin", u"Доложить генералу Воронину"),
    'task_vet_bring': ("Bring Lucky's PDA to the Barkeep", u"Принести КПК Счастливчика Бармену"),
    'task_amb_bring': ("Bring Tyran's PDA to the Barkeep", u"Принести КПК Тирана Бармену"),
    'item_lucky_name': ("Lucky's PDA", u"КПК Счастливчика"),
    'item_lucky_desc': ("The PDA of Lucky, the leader of the mad veterans.", u"КПК Счастливчика, главаря безумных ветеранов."),
    'item_tyran_name': ("Tyran's PDA", u"КПК Тирана"),
    'item_tyran_desc': ("The PDA of Tyran, the leader of the Mercs.", u"КПК Тирана, главаря наёмников."),
}
# SoC strings used under a coop_soc_duty_* name where the SoC dialog phrase id differs (redirect phrases that repeat a text)
SRC_ALIAS = {('vo', '811'): 'bar_dolg_leader_start_81'}
# authored text ids per dialog phrase (key, phrase id) -> AUTH key
AUTH_PHRASE = {('iv', 'I1'): 'iv_I1', ('iv', 'I2'): 'iv_I2', ('iv', 'I3'): 'iv_I3', ('iv', 'I5'): 'iv_I5', ('iv', 'I6'): 'iv_I6'}

# ---------------------------------------------------------------------------------------------------
# NPCs created by script (coop_soc_duty.script). x y z = SoC position of the same NPC (all.spawn / its walk path) where SoC has one.
# ---------------------------------------------------------------------------------------------------
NPCS = [
    # Bar (coop_l05_bar)
    dict(key='commander', level='coop_l05_bar', section='soc_duty_guard_commander', story=NPC['commander'], pos=(191.87, 0.0, 104.53), hostile=False,
         soc='all.spawn bar_dolg_regular_5 (story id bar_dolg_guard_commander)'),
    dict(key='ivancov', level='coop_l05_bar', section='soc_duty_ivancov', story=NPC['ivancov'], pos=(192.91, 0.0, 117.22), hostile=False,
         soc='all.spawn bar_dolg_ivancov'),
    # Wild Territory (coop_l06_rostok): the mad veterans' camp
    dict(key='lucky', level='coop_l06_rostok', section='soc_vet_lucky', story=NPC['lucky'], pos=(-250.7, 1.2, 14.7), hostile=True, pda='lucky',
         soc='path bar_evil_veterans_leader_walk'),
    dict(key='vet1', level='coop_l06_rostok', section='soc_vet_1', story=None, pos=(-247.3, 0.0, 7.0), hostile=True,
         soc='path bar_evil_veterans_guard_1_walk'),
    dict(key='vet2', level='coop_l06_rostok', section='soc_vet_2', story=None, pos=(-245.3, 0.0, 15.4), hostile=True,
         soc='path bar_evil_veterans_guard_2_walk'),
    # Wild Territory: Tyran and the Mercs of the construction site (only while the Tyran job is open, as the SoC spawner condition)
    dict(key='tyran', level='coop_l06_rostok', section='soc_tyran', story=NPC['tyran'], pos=(-234.3, 9.36, 49.0), hostile=True, pda='tyran', need=ASTART,
         soc='smart terrain ros_smart_stalker_killers1'),
    dict(key='merc1', level='coop_l06_rostok', section='soc_merc_1', story=None, pos=(-231.5, 9.36, 47.5), hostile=True, need=ASTART,
         soc='smart terrain ros_smart_stalker_killers1'),
    dict(key='merc2', level='coop_l06_rostok', section='soc_merc_2', story=None, pos=(-237.0, 9.36, 51.0), hostile=True, need=ASTART,
         soc='smart terrain ros_smart_stalker_killers1'),
    # the two ambush snipers of the way (SoC spawner condition bar_kill_svoboda_ambush_start)
    dict(key='amb1', level='coop_l06_rostok', section='soc_merc_3', story=None, pos=(-204.0, 0.0, 63.7), hostile=True, need=ASTART,
         soc='all.spawn bar_spy_killer_2, path bar_spy_freedom_walk3'),
    dict(key='amb2', level='coop_l06_rostok', section='soc_merc_4', story=None, pos=(-187.7, 0.0, 139.7), hostile=True, need=ASTART,
         soc='all.spawn bar_spy_killers_2, path bar_spy_freedom_walk2'),
]
# the Bulldog 6 of Voronin's job: SoC all.spawn mil_wpn_rg-6 (the stash in the Freedom village), story id Mil_RG6
RG6 = dict(level='coop_l07_military', section='wpn_rg-6', pos=(-274.55, -27.47, 245.41))
PDAS = {'lucky': dict(section='bar_lucky_pda', flag=LPDA, killed=VKILLED, npc='lucky'),
        'tyran': dict(section='bar_tiran_pda', flag=TPDA, killed=AKILLED, npc='tyran')}

# ---------------------------------------------------------------------------------------------------
# tasks (tm_coop_soc_duty.ltx). steps: (cond, text key, target story id); the last step has cond None
# text key: ('soc', SoC string id) or ('auth', AUTH key)
# ---------------------------------------------------------------------------------------------------
TASKS = [
    dict(id='bar_soc_dolg_community_task', icon='ui_inGame2_bar_start_go_to_yantar_quest_task',
         title=('soc', 'bar_dolg_community_quest'), complete='{+%s} complete' % OATH,
         open='CSTART and not OATH',
         steps=[('+%s +%s' % (RDONE, TDONE), ('soc', 'bar_dolg_community_quest_prisyaga'), NPC['voronin']),
                ('+%s' % RDONE, ('soc', 'bar_dolg_community_quest_recomendation'), NPC['ivancov']),
                ('+%s' % TDONE, ('soc', 'bar_dolg_community_quest_vernost'), NPC['voronin']),
                (None, ('soc', 'descr_bar_dolg_community_quest'), NPC['voronin'])]),
    dict(id='bar_soc_dolg_test_task', icon='ui_inGame2_ros_start_help_kruglov_quest_task',
         title=('auth', 'task_test_name'), complete='{+%s} complete' % TDONE,
         open='TSTART and not TDONE',
         steps=[('+%s' % ARENA, ('auth', 'task_test_back'), NPC['ivancov']),
                (None, ('auth', 'task_test_win'), NPC['arny'])]),
    dict(id='bar_soc_rg6_task', icon='ui_inGame2_mil_start_kill_lukash_quest_task',
         title=('soc', 'mil_freedom_rg6_task'), complete='{+%s} complete' % RDONE,
         open='RSTART and not RDONE',
         steps=[('+%s' % RGAIN, ('soc', 'mil_return_to_voronin'), NPC['voronin']),
                (None, ('soc', 'mil_rg6'), RG6_STORY)]),
    dict(id='bar_soc_veterans_task', icon='ui_inGame2_bar_start_sneak_into_the_x_18_lab_quest_task',
         title=('soc', 'bar_crazy_veterans_quest'), complete='{+%s} complete' % VDONE,
         open='VSTART and not VDONE',
         steps=[('+%s' % VKILLED, ('auth', 'task_vet_bring'), NPC['barkeep']),
                (None, ('soc', 'bar_kill_crazy_veterans'), NPC['lucky'])]),
    dict(id='bar_soc_ambush_task', icon='ui_inGame2_mil_start_report_to_max_quest_task',
         title=('soc', 'bar_dolg_svoboda_ambush_quest'), complete='{+%s} complete' % ADONE,
         open='ASTART and not ADONE',
         steps=[('+%s' % AKILLED, ('auth', 'task_amb_bring'), NPC['barkeep']),
                (None, ('soc', 'bar_dolg_kill_tiran'), NPC['tyran'])]),
    dict(id='bar_soc_leader_task', icon='ui_inGame2_mil_start_talk_to_the_cap_quest_task',
         title=('auth', 'task_leader_name'), complete='{+%s} complete' % KDONE,
         open='KSTART and not KDONE',
         steps=[('+%s' % KKILLED, ('auth', 'task_leader_back'), NPC['voronin']),
                (None, ('auth', 'task_leader_kill'), NPC['lukash'])]),
]

# SoC strings that become the specific-character names / bios / item texts of the new NPCs: new id -> SoC id
CHAR_STRINGS = {
    'coop_soc_duty_commander_name': 'bar_plichko_name', 'coop_soc_duty_commander_bio': 'bar_plichko_bio',
    'coop_soc_duty_ivancov_name': 'bar_ivancov_name', 'coop_soc_duty_ivancov_bio': 'bar_ivancov_bio',
    'coop_soc_duty_lucky_name': 'ros_happy_name', 'coop_soc_duty_lucky_bio': 'ros_happy_bio',
    'coop_soc_duty_tyran_name': 'ros_tiran_name', 'coop_soc_duty_tyran_bio': 'ros_tiran_bio',
}
