# Artifact fetch quests refusing the artifact

## Root cause
Every artifact has two item sections: the CoP-style `af_x` (configs/misc/artefacts.ltx) and a SoC-style twin `af_x_soc` (configs/misc/artefacts_soc.ltx, e.g. `[af_medusa_soc]` line 7). The mod's death/trade tables (death_items_by_levels.ltx:26+, trader trade ltx files) use the `_soc` sections, while the quest dialogs (dialogs_coop_l01_escape.xml:957-980, dialogs_coop_l05_bar.xml:1149-1171, yantar) call `dialogs_item.if_actor_has_af_*` / `transfer_af_*`, which in gamedata.db1/scripts/dialogs_item.script check only `first_speaker:object("af_x")`. A player holding `af_x_soc` is never recognised (dialog option hidden/refused) even though the in-game name is the same.

## Twin pairs (artefacts.ltx vs artefacts_soc.ltx)
medusa, cristall_flower, night_star, vyvert, gravi, gold_fish, cristall, blood, mincer_meat, soul, electra_sparkler, electra_flash, electra_moonlight, fireball, fuzz_kolobok, dummy_battery, dummy_glassbeads -> each `af_x` / `af_x_soc`.
SoC-only (renamed, no same-name twin): ameba_slime/slug/mica (vs af_mica/af_baloon/af_glass naming), dummy_spring, dummy_pellicle, rusty_thorn/kristall/sea-urchin, drops. CoP-only: af_eye, af_fire, af_ice, af_compass, af_oasis_heart, af_dummy_dummy (not twinned; af_eye quest unchanged).
Which twin spawns in the world is decided by the binary all.spawn zone lists (not inspectable here); loot/trade tables clearly use `_soc`, so both can reach the player.

## Fix
gamedata/scripts/dialogs_item.script: new helper `af_twin_section(actor, section)` returns `section` if held, else `section.."_soc"` if held, else nil. The has-check and transfer for the 8 quest artifacts (medusa, blood, cristall_flower, vyvert, gravi, gold_fish, cristall, fireball) use it, so whichever twin the player carries is accepted and removed. `hasnt` functions derive from `has`, so they follow.

## Confidence
High that the check is exact-section only and twins exist; medium-high that this is the visible symptom (spawn tables not verifiable).

## Multiplayer risks
Low. Check runs on first_speaker (talking player), same as before. If the talking player holds both, the plain `af_x` is taken first.

## Test
Give player `af_medusa_soc` (spawn via console), take Sidorovich's medusa quest, talk: hand-over option should appear and consume it. Repeat with plain `af_medusa`, and with Barman (vyvert/gravi/gold_fish).

## Diff
```diff
--- source/gamedata.db1/scripts/dialogs_item.script	2026-10-15 20:03:09.875044100 +0100
+++ patches/artifact_quests/gamedata/scripts/dialogs_item.script	2026-10-15 20:37:20.823522700 +0100
@@ -1,4 +1,17 @@
 
+-- Artifacts exist in two variants: "af_x" and the SoC-style twin "af_x_soc" (artefacts_soc.ltx).
+-- Quests ask for "af_x" but the world may give the player the twin, so accept either.
+function af_twin_section(actor, section)
+	local obj = actor:object(section)
+	if obj ~= nil then
+		return section
+	end
+	if actor:object(section .. "_soc") ~= nil then
+		return section .. "_soc"
+	end
+	return nil
+end
+
 function if_actor_has_medkit(first_speaker, second_speaker)
 	return first_speaker:object("medkit") ~= nil
 end
@@ -13,7 +26,7 @@
 
 
 function if_actor_has_af_medusa(first_speaker, second_speaker)
-	return first_speaker:object("af_medusa") ~= nil
+	return af_twin_section(first_speaker, "af_medusa") ~= nil
 end
 
 function if_actor_hasnt_af_medusa(first_speaker, second_speaker)
@@ -21,13 +34,13 @@
 end
 
 function transfer_af_medusa(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_medusa")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_medusa") or "af_medusa")
 end
 
 
 
 function if_actor_has_af_blood(first_speaker, second_speaker)
-	return first_speaker:object("af_blood") ~= nil
+	return af_twin_section(first_speaker, "af_blood") ~= nil
 end
 
 function if_actor_hasnt_af_blood(first_speaker, second_speaker)
@@ -35,13 +48,13 @@
 end
 
 function transfer_af_blood(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_blood")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_blood") or "af_blood")
 end
 
 
 
 function if_actor_has_af_cristall_flower(first_speaker, second_speaker)
-	return first_speaker:object("af_cristall_flower") ~= nil
+	return af_twin_section(first_speaker, "af_cristall_flower") ~= nil
 end
 
 function if_actor_hasnt_af_cristall_flower(first_speaker, second_speaker)
@@ -49,13 +62,13 @@
 end
 
 function transfer_af_cristall_flower(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_cristall_flower")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_cristall_flower") or "af_cristall_flower")
 end
 
 
 
 function if_actor_has_af_vyvert(first_speaker, second_speaker)
-	return first_speaker:object("af_vyvert") ~= nil
+	return af_twin_section(first_speaker, "af_vyvert") ~= nil
 end
 
 function if_actor_hasnt_af_vyvert(first_speaker, second_speaker)
@@ -63,13 +76,13 @@
 end
 
 function transfer_af_vyvert(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_vyvert")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_vyvert") or "af_vyvert")
 end
 
 
 
 function if_actor_has_af_gravi(first_speaker, second_speaker)
-	return first_speaker:object("af_gravi") ~= nil
+	return af_twin_section(first_speaker, "af_gravi") ~= nil
 end
 
 function if_actor_hasnt_af_gravi(first_speaker, second_speaker)
@@ -77,13 +90,13 @@
 end
 
 function transfer_af_gravi(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_gravi")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_gravi") or "af_gravi")
 end
 
 
 
 function if_actor_has_af_gold_fish(first_speaker, second_speaker)
-	return first_speaker:object("af_gold_fish") ~= nil
+	return af_twin_section(first_speaker, "af_gold_fish") ~= nil
 end
 
 function if_actor_hasnt_af_gold_fish(first_speaker, second_speaker)
@@ -91,13 +104,13 @@
 end
 
 function transfer_af_gold_fish(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_gold_fish")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_gold_fish") or "af_gold_fish")
 end
 
 
 
 function if_actor_has_af_cristall(first_speaker, second_speaker)
-	return first_speaker:object("af_cristall") ~= nil
+	return af_twin_section(first_speaker, "af_cristall") ~= nil
 end
 
 function if_actor_hasnt_af_cristall(first_speaker, second_speaker)
@@ -105,13 +118,13 @@
 end
 
 function transfer_af_cristall(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_cristall")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_cristall") or "af_cristall")
 end
 
 
 
 function if_actor_has_af_fireball(first_speaker, second_speaker)
-	return first_speaker:object("af_fireball") ~= nil
+	return af_twin_section(first_speaker, "af_fireball") ~= nil
 end
 
 function if_actor_hasnt_af_fireball(first_speaker, second_speaker)
@@ -119,7 +132,7 @@
 end
 
 function transfer_af_fireball(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "af_fireball")
+	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, af_twin_section(first_speaker, "af_fireball") or "af_fireball")
 end
 
 
```
