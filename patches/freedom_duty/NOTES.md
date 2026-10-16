# Freedom/Duty hostility fix (Army Warehouses, coop_l07_military)

## Root cause
Every Freedom NPC logic in `configs\scripts\coop_l07_military\*.ltx` has `on_hit = hit@freedom_bad_reputation[_N]`
whose section is `on_info = %=mil_dolg_increase_goodwill%` (e.g. mil_smart_terrain_12_walker_cap.ltx:6,17-18;
21 files, ~70 sections). The `on_info` has NO condition, and the `hit` scheme (vanilla `xr_hit.script`,
action_process_hit:hit_callback) fires for a hit from ANY source: Duty bullets, grenades, mutants, stray rounds.
The effect (found in the packed `gamedata.db1` only, mod's client `xr_effects.mil_dolg_increase_goodwill` ->
`game_cl.executeFunctionOnServer("mil_dolg_increase_goodwill")` -> server fn) does:
`inc_faction_goodwill_to_actor("dolg", +5000)` and `("freedom", -5000)`.
`xr_effects.inc_faction_goodwill_to_actor` (xrmpe_patch xr_effects.script:1886-1897) loops over **all** `db.mp_actors`
and calls `relation_registry.change_community_goodwill`, so it is **global to every player**; value is clamped to
[-3000, 1000] (game_relations.ltx `community_goodwill_limits`) and is saved, so it persists across reloads.
Consequences matching the reports: Duty attacks Freedom at the farm/fence -> Freedom NPCs get hit -> Freedom goes
hostile and Duty goes green for all players; "kill the Duty squad before the fence" works because no Freedom NPC
is ever hit; "Freedom hostile as soon as you enter" / "from any shooting nearby" = any damage to a Freedom NPC.
After "report to Max" (`mil_freedom_increase_goodwill`, tm_coop_l07_military.ltx:128) Duty attacks Freedom ->
same path flips Freedom back to hostile.

Skull dialog lock: character `mil_smart_terrain_18_duty_skull` (character_desc_coop_l07_military.xml:264-266) has
`start_dialog` = a single NPC line (dialogs_coop_l07_military.xml:3-10, no `<next>`, no `break_dialog`). Once its
quest dialogs are used up (`..SKULL_1_STOP_DIALOG_INFO` given, assault dialog not yet unlocked) no actor
choice remains, so the player has no reply and no exit. Every other Freedom NPC in that file lists
`actor_dialog actor_break_dialog` (vanilla dialogs.xml:13, priority -5 "goodbye") as the fallback; Skull (and the
two snipers, see below) lacked it.

## Changes
1. 21 files in `gamedata\configs\scripts\coop_l07_military\`: `on_info = %=mil_dolg_increase_goodwill%` ->
   `on_info = {=hit_by_actor} %=mil_dolg_increase_goodwill%`. `hit_by_actor` is the existing xrmpe condition
   (xr_conditions.script:935; true only if `db.storage[npc].hit.who` is a player actor). So only a player
   attacking Freedom turns Freedom hostile / Duty friendly (intended "bad reputation" behaviour kept);
   Duty/mutant/crossfire hits no longer do.
2. `gamedata\configs\gameplay\character_desc_coop_l07_military.xml`: added `<actor_dialog>actor_break_dialog</actor_dialog>`
   to Skull so players can always leave/decline (fixes stuck dialog, gives Duty players a "refuse" exit).

## Relation scope (MP)
Community goodwill is applied to every player in `db.mp_actors` (global per server session, not per player).
Unchanged. Hits from any single player still flip all players, as before.

## Confidence / risks
- Confidence high (~85%) for the hit trigger being the main cause; medium for dialog fix (engine behaviour of a
  one-phrase dialog with no choices cannot be verified here; actor_break_dialog mirrors all sibling NPCs).
- If a player hits Freedom, hostility is still permanent for all players (one stray player bullet is enough);
  deliberately not softened (would need a counter whose MP storage semantics are unclear).
- `hit_by_actor` prints a debug line per hit (harmless). If `hit` storage lacked `who` the condition is false -> safe.
- Not touched (out of scope, same lock risk): `mil_smart_terrain_4_freedom_sniper_1` and
  `mil_smart_terrain_11_freedom_sniper_1` also lack `actor_break_dialog`.
- The mod's server/client effect definitions are in packed gamedata.db1 but missing from `source\`; not modified.

## How to test
1. Enter Army Warehouses, do nothing: Freedom stays neutral/green.
2. Accept Skull's quest, let Duty attack Freedom (don't shoot): Freedom still green to players, Duty unchanged.
3. Report to Max, let Duty fight Freedom: no change from crossfire; completing the report task sets Freedom friendly.
4. Shoot a Freedom NPC as a player: Freedom hostile, Duty friendly (expected).
5. Talk to Skull after accepting the quest: "goodbye" choice appears and closes the dialog.

## Diffs

```diff
--- a/configs/gameplay/character_desc_coop_l07_military.xml
+++ b/configs/gameplay/character_desc_coop_l07_military.xml
@@ -264,6 +264,7 @@
 	<start_dialog>mil_smart_terrain_18_duty_skull_start_dialog</start_dialog>	
 	<actor_dialog>mil_smart_terrain_18_duty_skull_kill_freedom_sniper_start_dialog</actor_dialog>	
 	<actor_dialog>mil_smart_terrain_18_duty_skull_talk_to_skull_about_the_assault_start_dialog</actor_dialog>		
+	<actor_dialog>actor_break_dialog</actor_dialog>
     </specific_character>
 	
 <specific_character id="mil_smart_terrain_18_duty_skull_partner_1" team_default = "1">
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_10_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_10_walker_freedom_ordinary.ltx
@@ -13,7 +13,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -31,7 +31,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -50,7 +50,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_3]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -68,6 +68,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_4]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_11_animpoint_freedom.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_11_animpoint_freedom.ltx
@@ -74,7 +74,7 @@
 use_camp 											= true
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -154,6 +154,6 @@
 use_camp 											= true
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_11_walker_max.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_11_walker_max.ltx
@@ -162,6 +162,6 @@
 meet_on_talking 									= true
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_11_walker_shurup.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_11_walker_shurup.ltx
@@ -30,6 +30,6 @@
 meet_on_talking 									= true
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_12_patrol_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_12_patrol_freedom_ordinary.ltx
@@ -12,7 +12,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -30,7 +30,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -48,7 +48,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_3]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -66,6 +66,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_4]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_12_walker_cap.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_12_walker_cap.ltx
@@ -15,6 +15,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_12_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_12_walker_freedom_ordinary.ltx
@@ -13,7 +13,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -32,7 +32,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -51,7 +51,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_3]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -70,7 +70,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_4]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -89,7 +89,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_5]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -108,7 +108,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_6]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -127,7 +127,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_7]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -146,7 +146,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_8]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -165,7 +165,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_9]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -184,7 +184,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_10]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -203,7 +203,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_11]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -222,6 +222,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_12]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_16_walker_freedom_security.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_16_walker_freedom_security.ltx
@@ -13,7 +13,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -32,6 +32,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_16_walker_lukash.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_16_walker_lukash.ltx
@@ -91,6 +91,6 @@
 meet_on_talking 									= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_2_guard_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_2_guard_freedom_ordinary.ltx
@@ -13,7 +13,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -32,6 +32,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_2_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_2_walker_freedom_ordinary.ltx
@@ -13,7 +13,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -32,7 +32,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -51,6 +51,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_3]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_3_patrol_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_3_patrol_freedom_ordinary.ltx
@@ -12,7 +12,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -30,6 +30,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_3_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_3_walker_freedom_ordinary.ltx
@@ -76,7 +76,7 @@
 use_camp 											= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -158,7 +158,7 @@
 use_camp 											= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -240,7 +240,7 @@
 use_camp 											= false
 
 [hit@freedom_bad_reputation_3]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -322,7 +322,7 @@
 use_camp 											= false
 
 [hit@freedom_bad_reputation_4]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -404,7 +404,7 @@
 use_camp 											= false
 
 [hit@freedom_bad_reputation_5]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -485,6 +485,6 @@
 use_camp 											= true
 
 [hit@freedom_bad_reputation_6]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_4_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_4_walker_freedom_ordinary.ltx
@@ -11,6 +11,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_4_walker_freedom_sniper.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_4_walker_freedom_sniper.ltx
@@ -32,6 +32,6 @@
 show_spot 											= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_5_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_5_walker_freedom_ordinary.ltx
@@ -12,6 +12,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_5_walker_freedom_sniper.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_5_walker_freedom_sniper.ltx
@@ -32,7 +32,7 @@
 show_spot 											= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -70,6 +70,6 @@
 show_spot 											= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_6_walker_freedom_sniper.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_6_walker_freedom_sniper.ltx
@@ -32,6 +32,6 @@
 show_spot 											= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_7_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_7_walker_freedom_ordinary.ltx
@@ -11,7 +11,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -28,6 +28,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_8_walker_freedom_sniper.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_8_walker_freedom_sniper.ltx
@@ -32,6 +32,6 @@
 show_spot 											= false
 
 [hit@freedom_bad_reputation]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```

```diff
--- a/configs/scripts/coop_l07_military/mil_smart_terrain_9_walker_freedom_ordinary.ltx
+++ b/configs/scripts/coop_l07_military/mil_smart_terrain_9_walker_freedom_ordinary.ltx
@@ -12,7 +12,7 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_1]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
 
@@ -30,6 +30,6 @@
 corpse_detection_enabled 							= false
 
 [hit@freedom_bad_reputation_2]
-on_info 											= %=mil_dolg_increase_goodwill%
+on_info 											= {=hit_by_actor} %=mil_dolg_increase_goodwill%
 
 ;================================================
\ No newline at end of file
```
