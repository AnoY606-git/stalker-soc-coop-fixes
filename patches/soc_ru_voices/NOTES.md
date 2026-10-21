# soc_ru_voices: original Russian voice for the SoC dialog lines

Planned changes line (EN): The Barkeep, Sidorovich (start dialog) and the Yantar scientists now speak with the original Russian voice when the voice language is Russian (before, those lines were silent in Russian).
Planned changes line (RU): Бармен, Сидорович (стартовый диалог) и учёные Янтаря теперь говорят оригинальными русскими голосами, когда язык озвучки русский (раньше эти реплики молчали по-русски).

## What and why
Our SoC dialog patches play recorded lines with `coop_soc_opening.voice_lang()` (`voice_language` = auto / rus / eng in the player's `coop_settings.ltx`). Only English recordings (Steam SoC) existed, so with `rus` the lines were silent. The maintainer FOSTER uploaded the original Russian SoC sounds (`sounds.zip`, 19353 entries, extracted offline, no path traversal, nothing executed; the only script file in it, `mp_actor\c1.cmd`, was not extracted). The Russian recordings of the same phrases ship here.

## Files (22 ogg, 2.70 MB, original SoC ogg files as they are, comment header kept)
Stock SoC path `gamedata\sounds\characters_voice\dialogs\<name>.ogg` (the English ones stay in `...\dialogs\eng\`, like the opening keeps `script_replics\trader\` for Russian and `eng\` for English):
- Barkeep, `bar_bar_barmen_start_<id>` for id 2, 221, 151, 15111, 171, 1721, 17212, 121, 13121, 1314 (10 files, `coop_soc_bar.script`).
- Sidorovich start dialog, `escape_trader_start_dialog_3` and `_321` (2 files, `coop_soc_opening.script`).
- Sakharov, `yantar_general_ucheniy_talk_start_<id>` for id 11, 211, 21111, 31, 3111, 311111, 61, 71, and Kruglov, `yantar_help_scientist_111111` and `_21` (10 files, `coop_soc_yan.script`).

## Shared files: `tools\apply_shared.py`
The Lua tables live in files that other patches ship, so they are changed by `python -I patches\soc_ru_voices\tools\apply_shared.py <repo root>` (idempotent: a second run changes nothing):
- `soc_dv_x18_quests\gamedata\scripts\coop_soc_bar.script`: `VOICE[id]` gets `rus = "characters_voice\\dialogs\\bar_bar_barmen_start_<id>"`.
- `soc_yan_x16_quests\gamedata\scripts\coop_soc_yan.script`: both tables get a `rus` slot, `voice_path` returns the path of the player's language (before: nothing unless `eng`).
- `cutscenes_pkg_opening\gamedata\scripts\coop_soc_opening.script`: lines 3 and 321 get `rus`.
- The offline tests (`mock_test.py` x3, `voice_lang_mock_test.py`), the in-game hooks (`*_hooks.lua`) and two NOTES.md lines of those patches are updated to say that Russian plays the Russian file.
Run it before `build.py`. Without it the recordings are shipped but unused (harmless).

## Checked, nothing to add
- `garbage_duty` commander (`duty_after_rush_good/_bad`): Russian already at the stock path in the mod, English under `eng\`.
- Opening trader lines (`script_replics\trader`): Russian already shipped.
- Not played with `voice_lang()`: `soc_mil_quests` (SoC has no Lukash / Max / Skull / Cap dialog voice, confirmed again, the archive has none), (`cutscenes_pkg_yantar` `dream_talk_l/_r` is now played per player, see the section below).

## Yantar dream voice (v1.4.2)
The ghost-sleep scene of `cutscenes_pkg_yantar` plays `dream_talk_l` / `dream_talk_r` (SoC `yan_dream_voices`); they were silent because the files were not in the media set. This patch ships both languages:
- Russian (FOSTER's `sounds.zip`, original SoC files as they are): `gamedata\sounds\characters_voice\scenario\yantar\dream_talk_l.ogg` (145,302 bytes) and `dream_talk_r.ogg` (141,048 bytes).
- English (Steam SoC 1.0006, extracted with `tools\xdb_soc.py`, `gamedata.db9`): `...\yantar\eng\dream_talk_l.ogg` and `dream_talk_r.ogg` (64,874 bytes each; in SoC the two are the same recording).
- `coop_scn_yantar.script` (patch `cutscenes_pkg_yantar`) picks the folder per player with `coop_soc_opening.voice_lang()` (same rule as the other dialogs, falls back to the game language), `eng\` for English, stock path for Russian. Offline test: `cutscenes_pkg_yantar	ests\dream_voice_mock_test.py` ALL PASS. Not played in the game (offline task).
Other `scenario\yantar\` files of the archive (Kruglov / professor lines, `ghost_pda`, `system_message_*`) are not used by any scene of the mod and are not shipped.

## Offline checks
Every referenced Russian file exists in this patch (mock tests of the three patches and `voice_lang_mock_test.py`: ALL PASS with `apply_shared.py` applied); `apply_shared.py` applied twice on a scratch copy; build with `--skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK; `check_conflicts.py` no new conflict. The real Russian audio was not played (game not launched, offline only).

## RU
Оригинальные русские реплики (sounds.zip от FOSTER) для строк, которые мы проигрываем через `voice_lang()`: Бармен (10 фраз), стартовый диалог Сидоровича (2), Сахаров и Круглов на Янтаре (10). Файлы лежат по стандартному пути `sounds\characters_voice\dialogs\`, английские остаются в `eng\`. Таблицы в Lua других патчей правит `tools\apply_shared.py` (идемпотентный, запускать перед `build.py`). Всего 22 ogg, 2,70 МБ. Игру не запускали.
