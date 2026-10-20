# AS Val special (wpn_val_m1) scope

`wpn_val_m1` (permanent scope, `scope_status = 1`) shows the bone `scope_pso_assault`, while its `scope_name = wpn_addon_scope` selects `[scope_pso1_val]` from the inherited `scopes_sect`: bone `scope_pso_sniper`, aim offset 0.11, the sniper reticle `wpn_crosshair_pso1sn`, zoom 25. Two PSO bones and mismatched aim data give the floating mark and the broken scope view.
Fix (`configs/weapons/w_val.ltx`, two lines in `[wpn_val_m1]`): show `scope_pso_sniper`, hide `scope_pso_assault`, so bone, reticle, zoom and aim offset describe the same PSO-1.
Not verified in game (no screenshot of the zoomed view; the SoC weapon configs could not be extracted for comparison). `wpn_abakan_m1`/`wpn_sig550_m1` use the same pattern and were not changed.

Кратко (RU): у `wpn_val_m1` кость прицела (assault) не совпадала с секцией прицела (sniper); выровнено на PSO-1 sniper. В игре не проверено.
