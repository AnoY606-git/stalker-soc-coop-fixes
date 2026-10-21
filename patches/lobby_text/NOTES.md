# Lobby / info text without the beta wording

## Root cause
The lobby text panel is `<auto_text>` `st_coop_desc` in `xrmpe_patch/configs/ui/coop_lobby_wnd.xml`. The same string id is defined twice in the add-on: `configs/text/<lang>/ui_st_screen_addon.xml` (the proper description) and `configs/text/<lang>/ui_st_coop_levels.xml` (the beta block "Shadow of COOP demo v1.2.2 ... перед переходом ... F5"). `ui_st_coop_levels.xml` is loaded last and wins (confirmed in game: `game.translate_string("st_coop_desc")` returned the demo text), so the lobby showed the demo block and the real description was hidden.

## What changed
`st_coop_desc` now has the same new text in all four files (rus/eng x both files) so load order cannot bring the beta text back: the maintainer's description (grammar fixed: opening quote added before X-Ray Multiplayer Extension, "рассчитанный" agrees with "аддон") only. Everything else in the four files is byte-identical to the originals (cp1251 kept).

## Tips removed (v1.4, maintainer's request)
The two tip lines ("Inventory is saved before moving to the next location" and "To pick a map manually, press F5 and vote") came from the old beta and overlapped the CHARACTER label at 1080p. FOSTER asked to cut them, so the panel now shows only the description.

RU: две строки-подсказки из старой беты (инвентарь сохраняется перед переходом; выбор карты через F5) убраны по просьбе FOSTER, остаётся только описание.

## Not changed
`metadata.json` inside coop.addon (launcher card) still says `"addonVersion": "v 7.0"`; it is outside gamedata so a .db patch cannot change it. The "Open Beta Test" label bottom-right of the lobby is engine/xrMPE.

## Tested
Real game test copy of coop.addon: lobby screenshot shows the new English text; log dump of `st_coop_desc` shows the new text. Russian text is the same file structure, checked by decoding the cp1251 output; not rendered in game (UI language was English in the test). At 800x600 the 5-line English text slightly touches the "LOBBY" label; at 1080p the panel is wider and fits (not rendered here).
