# Gray / Garbage hangar "Polny bespredel": bandits stay passive (code-only, UNTESTED in dedicated)

Cause (static): `gar_the_order_to_kill_gray_space_restrictor.ltx` gives `+GAR_THE_ORDER_TO_KILL_GRAY_INFO` with `on_actor_inside`, which tests
only `db.actor`. Every bandit (`gar_smart_terrain_6_walker_bandit_*`) sits in `..._idle` with `combat_ignore_cond = true` until that info exists
(`on_info = {+GAR_THE_ORDER_TO_KILL_GRAY_INFO} ..._attack`), so for a joined client the attack never starts. Gray stays `meet = no_meet` until
both bandit squads are dead (`animpoint ..._1` has `meet = meet`), which matches "can only talk to Gray after killing everyone".

Fix: `on_actor_inside` -> `on_any_player_inside` (any connected player entering starts the fight). Gray's later dialog is global
story-flag based (dialogs_coop_l02_garbage.xml, flag GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO), so any player can talk once both
bandit squads are dead.

Test so far: 1-player listen on the released addon, real restrictor ltx run through xr_logic.try_switch_to_another_section on a hub zone:
host inside -> flag set (PASS), nobody inside -> flag not set (PASS). Dedicated / 2 players: NOT run. The after-fix run was not done.
Other restrictors with the same keyword: see ..\any_player_restrictors\NOTES.md.
