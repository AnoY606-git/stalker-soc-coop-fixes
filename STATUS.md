# Patch status (2026-10-18)

Owner decision 2026-10-18: to save usage, agents whose code was written were stopped before their in-game tests finished.
"Written" below means the code exists but the in-game test was not completed; check each patch's NOTES.md before merging.

## Tested in game
- cnpp_shake, marked_one, lobby_text, cutscenes_core
- player_scaling (1/2/4 player census on Cordon and Garbage, real 2-client run; the save/load rescale fix is written, not tested)
- repeatable_quests (first pass; latest 2-client run: 4 PASS, 1 FAIL "refresh reached this client (offered again)")
- two-client harness (tools/stalker_xrmpe/run_coop.ps1, dedicated mode)
- quest_dialogs (Cordon, dedicated + client: options hidden without a quest, shown when accepted, hidden after hand-in; 5 PASS)
- task_guard (dedicated server: give_task with no spawned player no longer crashes; the held task reached the player after spawn).
  The released 8.1 dedicated server crashes this way on Cordon about 40 s after start when no player has spawned yet (2 of 2 runs).
- soc_music (SoC Bar radio song and menu music restored; tracks load with SoC lengths; PASS) and bar_speaker sound paths repaired
- soc_main_menu (UE4 remake menu video by Daniel Swahn / Ivan Sorce as the full screen background, 3 styles: ue4_b default text buttons, ue4_a SoC shutter panel, soc original art, switch with build.py --mm-style; 4:3 and 16:9 engine screenshots of every button page, no missing texture / script errors; the bar following a real mouse is not driven by the harness)
- no_mp_items (players spawn with the normal knife, torch and binoculars instead of mp_* versions; PASS)

## Written, not tested in game
- bar_speaker
- cutscenes_pkg_opening, cutscenes_pkg_endings, cutscenes_pkg_x18 / radar / yantar, cutscenes_pkg_monolith / pripyat, cutscenes_pkg_cats
- money_transfer
- campfires, stash_loot, stash_markers, alife_roaming
- no_grenade_tinnitus (config only)
- lumscale_presets (hook proven to run; `soc` / `bright` values are placeholders; preset file path may need `$logs$`)

## Known broken / incomplete
- cordon_technician: crashes when the technician spawns ("esc_rookie_technician13031"); do not merge
- mutant_loot: probe stage only; do not merge
- repeatable_quests: refresh after cooldown not offered again on a client (see above)

## Released (8.1) bugs being fixed now
- arena: players report the arena cutscene never finishes (our 8.0 change, never run in game)
- freedom_duty: siding with Freedom, hitting a Duty NPC turns Freedom hostile (our 8.0 change, never run in game)

## Fixed in passing
- repeatable_quests: the `[list]` in coop_repeat_quests.ltx held every generated `rq_*` quest three times (56 duplicates removed).

## v1.4 queue (2026-10-19)
- mutant_loot: DONE, 2 real clients on Cordon 24 PASS (one part per corpse, no duplicate), default chance no crash; bind_monster.script merged into darkvalley_restore. Ship together with darkvalley_restore.
- In progress: host armor reset + spawn direction + weapon_upgrades/npc_attachments boot-safety (gear agent), CNPP lag (cnpp agent), Kruglov follow + Ghost corpse (yantar agent), Sarcophagus door/wave chain proof.
- inventory_carry (2026-10-21): rewritten. Root cause of 'clients lose their kit after a load' and 'wrong weapon in the slot': after a load the engine spawns a NEW start-kit body per player and leaves the saved body as an uncontrolled orphan. Fix moves items and money (transfer_item, slots first) from the old body to the live one and releases the old body. Proven: dedicated + 1 client, first load (slots, money, item counts, 1 body). Not yet proven: second load in a row and 2 clients with the final ping-based version (host PC ran out of commit memory, firefox leak). NOT in the release skip list any more only after those runs.
