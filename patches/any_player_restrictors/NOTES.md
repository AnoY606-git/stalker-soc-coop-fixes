# any_player_restrictors (UNTESTED, code-only 2026-10-19)

Cause: `sr_idle` evaluates `on_actor_inside` against `db.actor` only (one actor object per process; the test logs showed id 0 on the
listen host), so a story restrictor may never fire for a joined client or on a dedicated server. The mod already has `on_any_player_inside`
(xr_logic.script, `utils.any_player_in_zone`), used by sr_no_weapon_space_restrictor.ltx.

Change: only the keyword `on_actor_inside` -> `on_any_player_inside` (CRLF kept), 32 files, all one-way story/spawn triggers:
esc_sirena, esc_the_order_to_attack_the_players, gar_the_order_to_kill_yurik, gar_waiting_for_the_order_to_kill_yurik, agr_sirena,
agr_stalker_help, agr_start_return_to_the_surface_task_end, agr_the_order_to_kill_mole, agru_bloodsucker_roar, agru_controller_roar,
agru_go_to_the_agroprom_underground_end, val_bloodsucker_roar, val_smart_terrain_12_walker_borov_attack,
val_smart_terrain_15_stalker_scammer_fail_info, val_smart_terrain_16_m_all_players_message_sos_signal,
val_smart_terrain_16_stalker_lucky_end_info, val_start_fake_gauss_1_quest_task, x18_start_get_out_of_the_lab_quest_task,
x18_smart_terrain_5_m_poltergeist, x18_spawn_dev_document_1_3_x18, x16_controller_roar, x16_smart_terrain_{1,2,3,4,5,6,8}_*,
x16_start_find_the_installation_quest_task_info, x16_start_get_out_of_the_lab_task_info (yantar),
yan_smart_terrain_1_walker_kruglov_go_to_saxarov, yan_smart_terrain_6_m_spawn_squad.
(The Gray restrictor gar_the_order_to_kill_gray is in patches\garbage_gray.)

SKIPPED on purpose (need design, not a keyword swap):
- gar_player_meeting_place, gar_player_sniper_place: inside/outside state machines with per-player info toggles (+/-GAR_*_PLACE_INFO, tasks);
  would need `on_no_players_inside` pairing.
- yan_start_take_measurements_1..3: `=actor_has_item(yan_psi_detector)` is per player, plus outside pairs.
- mil_cap_pda_1: `=isClient` makes it client-local by design.
- gar_duty_rush, ros_sniper_see: only `play_sound` (local effect). x10_save_st_turn_off_the_radar: scenario_autosave only.

Install: copy `gamedata` over the mod like the other patches.
Next step: test bot `freedom_fix\fd_hook.lua` (scratchpad, cfg gray=1) with 2 clients on dedicated before/after.
