# X18 documents hand-in at the Barman

## Root cause
Hand-in dialog `bar_smart_terrain_1_stalker_barmen_1_has_documents_darkvalley_dialog`
(source/gamedata.db0/configs/gameplay/dialogs_coop_l05_bar.xml:867-920) requires, via three
`<precondition>` lines (868-870), `dialogs_coop_l05_bar.if_actor_has_dev_document_{1,2,3}_x18`
(source/gamedata.db1/scripts/dialogs_coop_l05_bar.script:41-62), and `dont_has_flag
..._HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO`. Each precondition was
`first_speaker:object("dev_document_N_x18") ~= nil`, i.e. ALL THREE docs must be in the inventory of
ONE specific object (first_speaker), and that object is assumed to be the player. Nothing in the
precondition, in any info portion, in `on_item_take` (bind_stalker.script:162, 503) or in the task
logic references the keycard or pickup order.

Findings on the "order matters" reports:
- No script/config grants an info on pickup that the dialog later reads. The doc tasks
  (tm_coop_l04_x18.ltx:5-33) set `X18_START_GO_TO_X18_DOC_N_TASK_INFO` on `actor_has_item`, but the
  dialog never checks those infos. The doc tasks are only issued after the keycard task completes
  (tm_coop_l05_bar.ltx:12 -> val_start_sneak task -> tm_coop_l04_darkvalley.ltx:12), which is the
  only real "card first" coupling and it affects tasks/journal only, not the dialog.
- Docs 1 and 3 spawn when the first player enters the lab trigger
  (x18_spawn_dev_document_1_3_x18_space_restrictor.ltx:5), doc 2 is a level-placed item. In co-op
  these end up spread over whoever grabbed them; `actor_has_item` for tasks is party-wide on the
  dedicated server (xr_conditions.script any_actor_has_item) but the dialog check was per-player.
  A "replay in order" almost certainly meant one player collected everything. This is the most
  likely explanation for "3 docs + card, no hand-in" and "need all three at once"; I could not
  reproduce or fully prove it without running the game (confidence medium).
- Also possible: `first_speaker` is not always the player; `dialogs.relocate_item_section_from_actor`
  itself uses `dialogs.who_is_npc` (dialogs.script:591) to resolve the actor, which the old checks did not.

## Change
Only `gamedata/scripts/dialogs_coop_l05_bar.script`: the three `if_actor_has_dev_document_N_x18`
checks now (a) resolve the real player via `dialogs.who_is_npc`, (b) accept the document if the
talking player OR any living player in `db.mp_actors` holds it. Transfer only moves the copies the
talker actually holds (existing `relocate_item_section_from_actor`); documents held by another
player stay with them (no cross-player transfer_item, to avoid unsupported MP events). Public
function names are unchanged, so no XML change is needed.

## Not changed / notes
- The dialog sets its STOP flag only at phrase 6 while documents are transferred at phrase 1; if the
  dialog is aborted in between, docs are gone and the dialog is gone. Fixing that needs an XML edit
  (give_flag on phrase 1); left alone as out of scope.
- X18 codes exist in configs\text\eng\st_quest_items.xml: doc #1 "3826", doc #2 "4238" (matches
  x18_codedoor_key_*.ltx). Doc #3 has no code. Note x18_codedoor_3.ltx and x18_codedoor_key_3.ltx use
  X18_CODEDOOR_2 info/code 4238 (looks intentional/copied, left alone). The scientist body not
  spawning is by design (code is in the description). Lab-save crash not investigated.

## Multiplayer risks
- `v:object(section)` on remote players relies on their inventory being replicated to the client
  (same pattern as xr_conditions.any_actor_has_item). If it is not, behaviour falls back to the old
  per-talker check. The loop is guarded for nil `db.mp_actors`.
- A player can hand in while a teammate still holds a doc; that doc is not consumed.

## Test
1. 2 players: P1 holds docs 1+2, P2 holds doc 3; P1 talks to Barman -> hand-in dialog appears,
   P1's docs consumed, flag set, Yantar task given.
2. Solo with all 3 docs, picked up before/after the keycard -> dialog appears.
3. Only 2 docs in party -> no dialog.

## Diff
```diff
--- ../../source/gamedata.db1/scripts/dialogs_coop_l05_bar.script	2026-10-15 20:03:09.873536400 +0100
+++ gamedata/scripts/dialogs_coop_l05_bar.script	2026-10-15 20:39:53.037704100 +0100
@@ -26,8 +26,35 @@
 
 
 
+-- X18 documents hand-in.
+-- The talking player is not always first_speaker (see dialogs.who_is_npc), and the three
+-- documents may be spread over several co-op players, so look the item up on the real actor
+-- first and then on every living player. Pickup order / card order does not matter here.
+local function x18_doc_holder(first_speaker, second_speaker, section)
+	local npc, actor = dialogs.who_is_npc(first_speaker, second_speaker)
+	if actor ~= nil and actor:object(section) ~= nil then
+		return actor, actor
+	end
+	if db.mp_actors ~= nil then
+		for k, v in pairs(db.mp_actors) do
+			if v:alive() and v:object(section) ~= nil then
+				return v, actor
+			end
+		end
+	end
+	return nil, actor
+end
+
+local function x18_doc_transfer(first_speaker, second_speaker, section)
+	local holder, actor = x18_doc_holder(first_speaker, second_speaker, section)
+	-- documents held by another player stay with them; only the talker's copy is handed over
+	if holder ~= nil and actor ~= nil and holder:id() == actor:id() then
+		dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, section)
+	end
+end
+
 function if_actor_has_dev_document_1_x18(first_speaker, second_speaker)
-	return first_speaker:object("dev_document_1_x18") ~= nil
+	return x18_doc_holder(first_speaker, second_speaker, "dev_document_1_x18") ~= nil
 end
 
 function if_actor_hasnt_dev_document_1_x18(first_speaker, second_speaker)
@@ -35,11 +62,11 @@
 end
 
 function transfer_dev_document_1_x18(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "dev_document_1_x18")
+	x18_doc_transfer(first_speaker, second_speaker, "dev_document_1_x18")
 end
 
 function if_actor_has_dev_document_2_x18(first_speaker, second_speaker)
-	return first_speaker:object("dev_document_2_x18") ~= nil
+	return x18_doc_holder(first_speaker, second_speaker, "dev_document_2_x18") ~= nil
 end
 
 function if_actor_hasnt_dev_document_2_x18(first_speaker, second_speaker)
@@ -47,11 +74,11 @@
 end
 
 function transfer_dev_document_2_x18(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "dev_document_2_x18")
+	x18_doc_transfer(first_speaker, second_speaker, "dev_document_2_x18")
 end
 
 function if_actor_has_dev_document_3_x18(first_speaker, second_speaker)
-	return first_speaker:object("dev_document_3_x18") ~= nil
+	return x18_doc_holder(first_speaker, second_speaker, "dev_document_3_x18") ~= nil
 end
 
 function if_actor_hasnt_dev_document_3_x18(first_speaker, second_speaker)
@@ -59,5 +86,5 @@
 end
 
 function transfer_dev_document_3_x18(first_speaker, second_speaker)
-	dialogs.relocate_item_section_from_actor(first_speaker, second_speaker, "dev_document_3_x18")
-end
\ No newline at end of file
+	x18_doc_transfer(first_speaker, second_speaker, "dev_document_3_x18")
+end
```
