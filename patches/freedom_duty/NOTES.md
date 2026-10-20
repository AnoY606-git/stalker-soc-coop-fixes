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

## Update 2026-10-18 (second pass after tester report: siding with Freedom, one shot at Duty flips Freedom hostile)
STATUS: PAUSED by owner request. Done / left / next step:
- DONE root cause (in-game proof, 1-player listen, released addon): `hit@freedom_bad_reputation` fires on ANY player hit on a
  Freedom NPC, including a stray bullet while the player is already on Freedom's side. Run result before the fix:
  `fd_logic_freedom_side_stray_hit_on_freedom_no_flip` FAIL (goodwill dolg -3000/freedom 1000 became dolg 1000/freedom -3000),
  same for the Lukash file. Crossfire (hit by an NPC) never flips (PASS), plain/duty-side behaviour unchanged (PASS).
  Logs: scratchpad `freedom_fix\res\L2_before_listen1p`.
- DONE fix: the 52 `on_info` lines now read `{=hit_by_actor -MIL_SMART_TERRAIN_3_FREEDOM_LUKASH_HELP_FREEDOM_STOP_DIALOG_INFO}`
  (no flip once the player sided with Freedom). Same test after the fix: 9/9 PASS (`res\L3_after_listen1p`).
- Test method: lobby stage (`game.IsLobbyStage()` true, READY needs a human click) keeps Army Warehouses offline, so the real shipped
  hit condlists are run through xr_logic on a hub NPC (test bot `fd_hook.lua`, scratchpad). The real cabin fight was NOT run.
- LEFT: 2-player dedicated run (before/after), Gray test after-fix runs, why Duty/Freedom NPCs do not die in the cabin fight.
- NEXT: run `go.ps1` D1 (dedicated 2p before), then the same with ExtraDir = freedom_duty + garbage_gray gamedata; write the Russian summary.
- Gray (patches\garbage_gray): `gar_the_order_to_kill_gray_space_restrictor.ltx` uses `on_actor_inside` (single db.actor), changed to
  `on_any_player_inside`. 1p listen before-run: host triggers fine (PASS), so the bug is for joined clients/dedicated: still to prove.

## Code-only pass 2026-10-19 (nothing below was run in game: all UNTESTED)
Owner decision: no game launches. Items marked UNTESTED come from static analysis of the shipped scripts/configs only.

### Report: "Duty and Freedom became friends, and when you kill Duty, Freedom becomes an enemy" (UNTESTED)
- No death hook exists: grep over coop_l07_military scripts, tm_coop_l07_military.ltx, dialogs and squad_descr finds
  `mil_dolg_increase_goodwill` / `mil_freedom_increase_goodwill` only in the 52 `hit@freedom_bad_reputation` sections and two task
  `on_complete` lines. `game_relations.ltx` keeps dolg<->freedom at -5000 both ways, all Duty/Freedom characters have the right
  community, squads have no `relationship` override: the two factions are enemies to each other in the data, as in SoC.
- What the player sees as "friends" is the PLAYER relation: before siding, both communities are neutral to the player; one hit flips both
  at once (Dolg +5000 clamped to +1000, Freedom -5000 clamped to -3000) for every player.
- Killing Duty with explosives or penetrating rounds also hits Freedom NPCs standing next to or behind the target. `hit_by_actor` is true
  for that hit, so the Freedom hook fires and Freedom turns hostile. A kill needs a final hit, so it looks like the death turned Freedom hostile.
- Fix = the guard already applied (`-MIL_SMART_TERRAIN_3_FREEDOM_LUKASH_HELP_FREEDOM_STOP_DIALOG_INFO` in the 52 lines): once the player is with
  Freedom, no hit on Freedom NPCs (stray, splash, penetration) changes relations. An unsided player who hits Freedom still turns Freedom
  hostile (quest design). Engine attack/kill goodwill values in game_relations.ltx are unchanged (SoC values).

### Cabin fight where nobody dies (analysis only, no file changed, UNTESTED)
`invulnerable = true` counts per file: animpoint_duty 33, walker_skull 9, walker_max 8, animpoint_freedom 10, freedom_ordinary (smart 3) 30,
lukash 3, monolith guard 8.
- Duty (`mil_smart_terrain_14_*`): true only in the waiting/salute/hide phases (animpoint, ambush_idle, salutuiu, active_dinamit_3) and after
  `MIL_SMART_TERRAIN_16_FREEDOM_1_SQUAD_DEAD` (kill_lukash). The fighting sections (`ambush_start_*`, `skull_partner_ambush_go_*`,
  `active_dinamit_1/2`) are `false`, so Duty can die during the assault as designed.
- Freedom assault NPCs (`walker_max_partner_ambush_go_*`, smart 3/11, state `hide_fire`) plus Lukash and Max are `true` for the whole fight:
  story protection of the attackers. "A minute of fire, nobody dies" fits invulnerable attackers that stay in `hide_fire` shooting at range.
  Changing these flags would not match the designed scenario and the cause cannot be confirmed without running the fight (the lobby stage keeps
  the level offline in the test bot), so no file was changed. Next step for whoever can run it: log health of Duty NPCs in `ambush_start_*`
  while the Freedom `ambush_go_*` NPCs fire.

### Gray and other restrictors
See `..\garbage_gray\NOTES.md` and `..\any_player_restrictors\NOTES.md` (both UNTESTED in dedicated mode).

### Краткое резюме для FOSTER (RU)
Проблема: на Армейских складах одиночный выстрел игрока по фрисдому делал всю Свободу враждебной (Долг +5000, Свобода -5000 для всех игроков).
Причина: у всех NPC Свободы в схеме hit стоит `on_info = %=mil_dolg_increase_goodwill%`, и оно срабатывает на ЛЮБОЕ попадание игрока,
в том числе случайное (стрельба по Долгу в толпе, пробитие, взрыв). Отдельного хука на смерть Долга нет: «смерть» выглядит так, потому что
последнее попадание тоже может прийтись по NPC Свободы.
Что сделано: в 52 строках 21 файла `coop_l07_military/*.ltx` условие стало `{=hit_by_actor -MIL_SMART_TERRAIN_3_FREEDOM_LUKASH_HELP_FREEDOM_STOP_DIALOG_INFO}`:
после выбора стороны Свободы попадания игрока больше не меняют отношения. Для игрока без выбора стороны и на стороне Долга поведение прежнее.
Проверено в игре (1 игрок, listen): до патча 3 теста FAIL, после патча 9/9 PASS (логика hit-схемы на NPC в лобби, не бой на самой локации).
НЕ проверено: бой у хижины Долга (лобби не даёт запустить уровень без ручного нажатия READY), 2 игрока на dedicated, непобиваемость NPC.
Похожая ошибка у ангара Серого и ещё 32 триггеров: `on_actor_inside` смотрит только на одного актёра (db.actor); заменено на `on_any_player_inside`
в `patches\garbage_gray` и `patches\any_player_restrictors` (всё НЕ проверено на dedicated).

### Freedom attackers made vulnerable in the counterattack (code-only 2026-10-19, UNTESTED)
Owner checked SoC: Max and his men counterattack Skull's Duty squad and the fight is lethal both ways (Max often dies; if alive he gives the flash drive quest).
Changed `invulnerable = true` -> `false` ONLY in the nine march/fight sections `*ambush_go*` (Duty fight sections were already vulnerable):
- `mil_smart_terrain_11_walker_max.ltx`: walker@mil_smart_terrain_11_walker_max_ambush_go (Max)
- `mil_smart_terrain_3_walker_freedom_ordinary.ltx`: walker@mil_smart_terrain_3_walker_max_partner_ambush_go_3..8 (6 NPCs)
- `mil_smart_terrain_11_animpoint_freedom.ltx`: walker@mil_smart_terrain_11_walker_max_partner_ambush_go_1..2 (2 NPCs)
Kept invulnerable (not combat): waiting/laugh/idle sections at base, `max_go_collect`, the post-fight animpoints and `max_idle` after
`MIL_SMART_TERRAIN_14_DUTY_SKULL_SQUAD_DEAD`, Lukash at base. Same file set also carries the hit_by_actor guard above.
Follow-ups checked statically:
- Quest completion does not depend on Max: `mil_start_kill_skull_quest_task` completes on `+MIL_SMART_TERRAIN_14_DUTY_SKULL_SQUAD_DEAD`
  (set by the squad `on_death` in squad_descr_coop_l07_military.ltx) and `mil_start_kill_the_duty_N` on `..._DUTY_N+1_SQUAD_DEAD`; "report to Max"
  already completed earlier by the Max dialog flag. If Max dies, only his post-fight `max_idle` section is never reached.
- The flash-drive quest does NOT exist in the mod data (no flash/drive dialog, task or item in dialogs_/tm_/character_desc_coop_l07_military), so
  nothing was added; it would need a new dialog + task (not invented here). Risk: Max dying now removes the Freedom-side talker for any such quest.

## Max's flash drive quest (ported from original SoC, code-only 2026-10-19, UNTESTED)
Source (original SoC data in soc_ai_port\extracted\src): `dialogs_military.xml` (mil_max_dialog 4003-4007, 40051/400511, 5001/5002, 6001, 400521-400523),
`soc_items.ltx` [crazy_flash], `st_soc_strings.xml` (Russian original text, kept 1:1 in rus; English is my translation), `mil_stalker0012.ltx`
(insane stalker, paths mil_zomb_stalker_walk/look present in coop_l07_military level.game), `dialogs_military.script` (transfer_flash, reward wpn_walther
= "Black Hawk"). Original flow: after the counterattack Max offers the job -> bring the flash drive from the insane stalker in the swamp -> hand it to Max -> gun.
Mod implementation (story flags, synced; every player):
- Dialogs on Max (`dialogs_coop_l07_military.xml` + 3 `<actor_dialog>` lines in character_desc): `..._flash_offer_dialog` (needs flags
  MAX_HELP_FREEDOM_STOP_DIALOG_INFO + MIL_SMART_TERRAIN_14_DUTY_SKULL_SQUAD_DEAD, i.e. Freedom path and Skull fight done; gives MIL_MAX_FLASH_JOB_INFO),
  `..._flash_wait_dialog` ("What, already?" when the player has no flash), `..._flash_report_dialog` (precondition: talker holds crazy_flash; hands it over,
  gives MIL_MAX_FLASH_JOB_COMPLETE_INFO). Dialog only exists on Max, so it is only available while he is alive.
- Script `scripts/dialogs_coop_l07_military.script` (new): if_actor_has_/hasnt_crazy_flash, transfer_crazy_flash.
- Tasks in `tm_coop_l07_military.ltx`: `mil_start_max_flash_quest_task` (target squad mil_crazy_squad, completes on actor_has_item(crazy_flash), gives the return task)
  and `mil_start_max_flash_return_quest_task` (target Max, completes on MIL_MAX_FLASH_JOB_COMPLETE_INFO, `reward_item = wpn_walther` for EVERY player, like other
  tm rewards). Task 1 is given by the existing report-to-Max restrictor (`mil_start_report_to_max_quest_task_space_restrictor.ltx`, new section sr_idle@flash waits for MIL_MAX_FLASH_JOB_INFO).
- Item `crazy_flash` (quest_items_coop.ltx, quest_item = true, name/descr strings in st_quest_items eng+rus). Insane stalker: spawn section `mil_crazy_stalker`
  (spawn_sections_coop_l07_military.ltx), profile (npc_profile_addon.xml), specific character with the flash in `<supplies>` (community zombied = shoots everyone),
  squad `mil_crazy_squad` (squad_descr, spawn_point = path mil_zomb_stalker_walk2 = SoC spot, target smart mil_smart_terrain_13), created by the existing smart-13
  spawn restrictor, job `mil_smart_terrain_13_walker_crazy.ltx` registered in smart/mil_smart_terrain_13.ltx.
- Texts eng+rus: st_dialogs_coop_l07_military.xml (mil_max_flash_*), st_coop_l07_military_quest.xml (task names), st_quest_items.xml, st_characters.xml.
Not original / limitations (all UNTESTED, nothing was run):
- The 3 opener lines ("Max, do you have a job for me?", "Max, about that job...") are mod-style actor lines (SoC used a hidden hub); English text is my translation.
- The job (walker_1 path of smart 13) is not the SoC camper spot: smart-job paths get the smart prefix, the SoC paths have none, so the stalker spawns at the SoC spot
  but then walks to smart 13's walker point (the SoC "minefield swamp" position could not be kept without editing level.game).
- No PDA article ("mil_crazy_flash_info"), no coop_pda_phrases emitters (archive sync) for the new phrases, no Skryaga ammo follow-up (text only), reward gun has no extra ammo (as in SoC).
- `npc_profile_addon.xml` is also shipped by `cordon_technician`: this copy is its file plus the mil_crazy_stalker profile (superset; check_conflicts lists it, freedom_duty sorts last).
- Tools run: check_conflicts.py (only that known overlap), check_lua_escapes.py (no hit in the new script), lint_configs.py (new sections only show the same
  "MISSING PARENT quest_item_base/online_offline_group" noise as the existing entries because the lint input was a partial extraction). XML files parse.
Max dying in the counterattack (see section above) simply removes the offer: no Max, no dialog, no flash drive quest, as in SoC.
