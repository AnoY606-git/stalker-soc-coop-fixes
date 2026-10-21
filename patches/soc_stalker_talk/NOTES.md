# Generic stalkers talk like in SoC

FOSTER (2026-10-21): "In the original every stalker had only one dialog, 'What interesting things can you tell me?'; here we have a choice like in Call of Pripyat."

SoC (`config\gameplay\character_dialogs.xml` of Steam SoC 1.0006): start `dm_hello_dialog`, actor dialogs `dm_cool_info_dialog` (one question, one news answer,
`dialog_manager.init_cool_info_dialog`) and `dm_help_wounded_medkit_dialog`. The mod uses the xrMPE `character_dialogs.xml`: `hello_dialog`,
`dm_universal_dialog` (built by `dialog_manager.init_new_dialog`: "I would like to ask you something" -> per faction -> job / anomalies / news) and `actor_break_dialog`.

Fix: `gamedata\scripts\dialog_manager.dscript` (appended by xrMPE to the base `dialog_manager.script`, the mod has no copy of its own) redefines
`init_new_dialog`: one actor question `soc_dm_cool_info_actor` ("Что интересного можешь рассказать?" / "Got anything interesting to tell me?"),
answered with one of the base news phrases (`phrase_table.information`, same preconditions / actions / "nothing else" endings as before).
Dialog id and precondition (`dm_universal_dialog`, `uni_dialog_precond`) are unchanged, so story NPCs and other dialogs are not touched.
Not tested in the game.

Кратко: у обычных сталкеров вместо меню из Зова Припяти один вопрос, как в ТЧ: «Что интересного можешь рассказать?», ответ одна новость.
