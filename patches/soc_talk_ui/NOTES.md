# Talk window in the look of Shadow of Chernobyl

Requested by FOSTER (maintainer of Shadow of COOP 8.1): make the dialog window look like the one in S.T.A.L.K.E.R.: Shadow of Chernobyl.

## What the SoC window has
Player panel top left (name, rank, group), partner panel top right (name, rank, group, relation), a big rusty speech frame with the
partner's name as header, a second rusty frame below it with the player's name as header and the answer list, a "Trade" button at the bottom edge.

## Where the pieces come from
All art and the layout belong to GSC Game World (S.T.A.L.K.E.R.: Shadow of Chernobyl 1.0006 and Call of Pripyat). Nothing is redrawn.
- The frame textures `ui_talk_dialogue*` (in `ui_numpad.dds`), the button `ui_button_main01` (in `ui_common.dds`) and the top/bottom shade
  (`ui_top_background`, `ui_bottom_background`) are still inside the Call of Pripyat base game, byte-identical to the SoC art. They are NOT shipped again.
- The two character panels (`ui_charinfo_left/right`) exist in the base game too, but recoloured blue. The rusty SoC panels are cut out of the
  SoC `ui_inventory2.dds` into one small texture `textures/ui/ui_soc_talk_charinfo.dds` (512x256 DXT5, 128 KB), ids in `configs/ui/textures_descr/ui_soc_talk.xml`.
- The layout numbers are the SoC `talk.xml` / `talk_16.xml` positions, scaled to the xrMPE UI space (wide 1920x1080, 4:3 1200x900).
- The NEYROCOOP "Shadow of Chernobyl" add-on was checked first and has no talk window xml (it uses the Call of Pripyat window), so it was no source.

## Why it needs a script
The xrMPE engine builds the talk window from `talk.xml` only (`main:answers_bcg`, `answers_list`, `questions_list`, `button`, the item blocks)
and has no character panels, no frame headers and no title text (SoC's engine had them). So the patch has two parts:
1. `configs/ui/talk.xml` (+ `talk_4x3.xml`): the frame bodies in the SoC look, the SoC "Trade" button, the lists moved to the SoC places. Every node the
   engine reads is still there (same names, same item blocks as the xrMPE file, only sizes and positions changed).
2. `scripts/soc_talk_ui.script` + `configs/ui/soc_talk_info.xml` (+ `_4x3`): a render-only window (`get_hud():AddDialogToRender`) that draws the shade, the two frame
   headers with the speakers' names, and the two character panels (portrait, name, RANK, GROUP, RELATION). It never takes input.
   Hook: `scripts/pda.dscript` is appended to the mod's `pda.script` and wraps `dialog_wnd_showed` / `dialog_wnd_closed` (the engine calls
   `pda.actor_menu_mode(10 / 11)` when the talk window opens / closes). The original functions still run first (the PDA archive sync stays intact).
   Every call is wrapped in `pcall`: if anything fails the talk window works as before (plain frame bodies and lists) and the log gets
   `[soc_talk_ui] show failed: ...`.
- Header art and titles live in the script window on purpose (so the draw order between the two windows cannot hide the names); the lists start below the headers.
- Rank: `character_rank()` against `game_relations:rating` (novice, experienced, veteran, master), group: `character_community()` ("stalker" and "actor" show as
  "Loner" / "Одиночка", the SoC wording, other groups use the PDA group names), relation: `relation()` (friend, neutral, enemy). Strings that exist are reused;
  only `ui_soc_talk_loner` is new (`configs/text/{eng,rus}/ui_st_soc_talk.xml`, other languages fall back to the base "Stalker").
- Partner: `actor:get_talk_partner_id()`, fallback the nearest online object that reports `is_talking()`.

## Files (one patch per file: no other patch ships any of these)
`configs/ui/talk.xml`, `talk_4x3.xml`, `soc_talk_info.xml`, `soc_talk_info_4x3.xml`, `configs/ui/textures_descr/ui_soc_talk.xml`,
`textures/ui/ui_soc_talk_charinfo.dds`, `scripts/soc_talk_ui.script`, `scripts/pda.dscript`, `configs/text/{eng,rus}/ui_st_soc_talk.xml`. Size: 153 KB raw.
`talk.xml` replaces the xrMPE `talk.xml` (the mod does not ship its own); nothing in the mod's scripts touches talk window controls by name (checked).

## Not changed / limits
- The trade button text is the base string `ui_st_trade` ("Торговля" in the Russian base, SoC says "Торговать"). Overriding the string would depend on string table load order, so it was left.
- Layout in 4:3 uses `talk_4x3.xml`; it relies on the engine picking `<name>_4x3.xml` for 4:3 screens like it does for `pda_4x3.xml` and the other windows.
- Not seen in game yet (offline task): see the test plan in the task report. Offline checks done: all XML parses, `tools/luabal.py`, `tests/mock_test.py` (the script logic with a mocked engine: names,
  icons, rank bands, group fallback, relation row, show/hide, no double add, errors swallowed), `build.py` BUDGET OK.

## Tests
- `tests/mock_test.py`: offline, needs `lupa`.
- `tests/talk_ui_hook.lua`: in-game hook for `run_coop.ps1 -Mode listen -Clients 1` (opens Sidorovich's window, two engine screenshots, asserts that the decoration window is in the render list while talking and removed after).

## RU
Окно диалога в стиле «Тень Чернобыля». Текстуры и раскладка принадлежат GSC Game World. Рамки `ui_talk_dialogue*`, кнопка `ui_button_main01` и затемнение сверху и снизу уже есть в базе
«Зова Припяти» (идентичны SoC), они не дублируются. Рыжие панели персонажей (в базе они синие) вырезаны из `ui_inventory2.dds` оригинального SoC в одну маленькую текстуру (128 КБ).
Движок xrMPE строит окно только из `talk.xml` и не умеет панели персонажей и заголовки рамок, поэтому патч состоит из двух частей: `talk.xml` (рамки, кнопка «Торговать», списки на местах SoC, все нужные
движку узлы сохранены) и скрипт `soc_talk_ui` (рисует затемнение, заголовки с именами и две панели: портрет, имя, ранг, группа, отношение). Скрипт подключается через `pda.dscript`, не берёт ввод и обёрнут в pcall:
при ошибке окно работает как раньше. Для 4:3 есть `talk_4x3.xml`. Текст кнопки остался базовым («Торговля»).
