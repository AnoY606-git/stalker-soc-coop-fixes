# Quest dialogs - notes

## Request
"Я хочу отказаться от заказа..." (cancel the order) and "Я по поводу задания..." (about the job) were always shown at
Sidorovich, Barman, Sakharov and Kruglov. They should only show while a quest from that NPC is running.

## Fix
- `gen_quest_dialogs.py <mod gamedata.db0>` adds one dialog-level `<precondition>` to every `*_secondary_quests_idle_dialog`
  and `*_secondary_quests_fail_dialog` (Escape, Bar, Yantar dialog files; Escape is built on top of `patches/cordon`'s copy).
- `gamedata/scripts/coop_quest_dialogs.script` (generated): a dialog is shown when at least one of its own answer phrases
  is open (all its has_flag set, none of its dont_has_flag set). For kill quests the quest's done flag (from
  `patches/repeatable_quests` coop_repeat_quests.ltx) also closes the cancel option once the target is dead.
- Flags are synced story flags, so the check is the same on every client. Repeatable quests clear the flags on repeat, so
  the options come back with the quest.

## Regenerate
Run the script again if the mod's dialog files or `patches/cordon`'s Escape dialogs change.

## Кратко (RU)
Пункты "Я хочу отказаться от заказа..." и "Я по поводу задания..." теперь видны только когда у игрока есть активное задание от этого НПС.

## 2026-10-21
`dialogs_coop_l01_escape.xml` was regenerated on top of `patches/cordon`'s copy again after the Sidorovich start dialog became the original SoC opening
(see `patches\cutscenes_pkg_opening\NOTES.md`); the only difference to cordon's copy is still the two `<precondition>` lines.

## 2026-10-21 technician parts
`dialogs_coop_l05_bar.xml` no longer has the two technician-parts dialogs of Plyushkin (`what_kind_of_junk_is_needed`, `hand_over_the_trash`); the generator drops them too. See `patches/no_tech_parts/NOTES.md`.
