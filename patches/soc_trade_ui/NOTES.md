# Trade window in the look of Shadow of Chernobyl

Requested by FOSTER (maintainer of Shadow of COOP 8.1): style the trade window like the one in S.T.A.L.K.E.R.: Shadow of Chernobyl.
He clarified that he means the LOOK only (rusty SoC frames, colours, fonts), not the layout: every position and size stays as it is now.

## What it does
Trade is a mode of the engine's actor menu (`configs/ui/actor_menu.xml`), the same window as the inventory and the loot window. The patch edits ONLY the nodes the
engine shows in trade mode and nowhere else:
- `left_delimiter` / `right_delimiter` (the partner side and the actor side of the trade window): new SoC texture, now a full-height column behind the two lists,
  the price rail and the weight rail. The three price texts inside (`trade_caption`, `trade_price`, `trade_weight_max`) keep their absolute screen position
  (their y is re-based because the node starts higher) and get the SoC fonts / colours (letterica, cream and dim cream like SoC's price row).
- `trade_buy_button` / `trade_sell_button`: the rust SoC button (`ui_button_main01` art, rebuilt for the button's own size), SoC orange caption `graffiti22` (ui_7),
  dark caption when highlighted or pressed.
Everything else in `actor_menu.xml` is byte for byte the source file (checked with diff, see below). The patch ships the mod's 16:9 `actor_menu.xml` and the
xrMPE `actor_menu_4x3.xml` (the add-on has no 4:3 file of its own; the engine uses the base one on 4:3 screens), both with the same edits.

## What matches SoC
Rusty frames (the lower centre panel of SoC's `ui_inventory2.dds`: rust bar, thin metal edges, dirty dark interior), the metal header band of the SoC panels
(as the price rail and the weight rail), the rust gear button with orange graffiti caption, SoC fonts and colours on the price row. Two identical columns, partner left,
player right, like SoC's two bags.

## What the engine prevents (so it is not in the patch)
- The SoC layout (centre item-description panel, two small offer lists in the middle, one "Trade" button) does not exist in the CoP actor menu: the engine has four lists
  (actor bag, partner bag, actor offer, partner offer), buy/sell buttons per side and one hover info window. FOSTER asked to keep positions anyway.
- Portrait, name, rank and group panel of the two characters, and the money boxes: `actor_ch_info`, `partner_ch_info`, `*_money_static` are shared with the
  inventory and loot windows, and the centre column (`main`) is shared too. They are NOT touched, so in the default build the top strip of each column and the centre column keep
  the Gunslinger art. Names ("Вещи Меченого", "Рюкзак") above the lists would need a header row the current positions do not leave room for.
- SoC says "Торговать" / "Уйти"; the engine buttons are "Buy" and "Sell" per side (base strings `ui_st_buy`, `ui_st_sell`), the price row shows "Total price" per side (SoC: "Цена").
- Item info panel (`actor_menu_item.xml`): the same hover window serves the inventory and loot windows, so it is left as it is.

## Other actor-menu modes
Inventory, loot, upgrade: unchanged (they use none of the edited nodes; `left_background` and `main` are not touched). If the engine ever showed the delimiters outside
trade mode they would show the SoC column too (the old Gunslinger delimiter art would have appeared there as well).

## Optional: top panels too
`optional/soc_trade_top/gamedata/configs/ui/actor_menu*.xml` make the delimiter columns start at y 0, so the SoC rust frame also covers the top strip (name, portrait, money)
of both sides. It is NOT the default because it depends on the engine drawing the delimiters BEFORE the character panels and money texts: if it draws them after, name, portrait and money would be
hidden. Test it once (test plan); copy the two files over the patch's `gamedata/configs/ui` if the names stay visible.

## Files (one patch per file: no other patch ships any of these)
`configs/ui/actor_menu.xml`, `actor_menu_4x3.xml`, `configs/ui/textures_descr/ui_soc_trade.xml`, `textures/ui/ui_soc_trade.dds` (1024x1024 DXT5, 1 MB: both layouts' columns and the
four button states). Size: about 1.0 MB raw. `tools/gen_soc_trade.py` regenerates everything from the SoC sheets (`ui_inventory2.dds`, `ui_common.dds`, read with `tools/xdb_soc.py`) and the two source xml files.
Nothing in the mod's scripts reads actor menu controls by name (checked; `pda.script` only gets `actor_menu_mode(2)` when trade opens).

## Credits
All art belongs to GSC Game World (S.T.A.L.K.E.R.: Shadow of Chernobyl). The frame and rail pieces are cut out of the original SoC sheets and recombined to fit the layout; nothing is redrawn.
The SoC panel art is not in the Call of Pripyat base game: its `ui_inventory2.dds`, `ui_common.dds` and `ui_trade_list_back.dds` differ from the SoC files (md5 checked, the base set is recoloured),
so the pieces are shipped, recomposed into one atlas (1 MB). Nothing byte-identical was available to reuse for these panels.

## Offline checks done
`diff` of both xml against their sources (only the nodes above differ), XML parses (the source files carry `--` inside comments, which strict parsers reject; the engine reads them, checked with the
comments stripped), `tools/check_conflicts.py` (no new conflicts), `build.py ... BUDGET OK` (db 43.4 MB, headroom 24.8 MB). Not seen in game (offline task).

## Test plan (one listen host, tests share the PC)
`tests/trade_ui_hook.lua` with `run_coop.ps1 -Mode listen -Clients 1` (command in the file header): teleports to Sidorovich, opens his talk window, `switch_to_trade()`, asserts that the
engine called `pda.actor_menu_mode(2)`, takes `stt_800x600_trade*` shots, closes it and then photographs 24 s (`stt_*_inv_N`) so the harness can press I for the normal inventory.
Repeat with `-Cfg vid=1280x720` (16:9, the real layout). Then once with `optional/soc_trade_top` laid over the stage. Log check: nothing about `ui_soc_trade` or `actor_menu` in the client log
(missing texture / xml errors).

## RU
Окно торговли в стиле «Тени Чернобыля». ФОСТЕР уточнил: менять нужно только вид (ржавые рамки, цвета, шрифты), позиции и размеры остаются прежними.
Торговля в движке это режим actor_menu (то же окно, что инвентарь и обыск), поэтому патч меняет только узлы, которые показываются при торговле: `left_delimiter`, `right_delimiter`
(колонки партнёра и игрока: рамки SoC за двумя списками, планки цены и веса, шрифты и цвета SoC у надписей цены) и кнопки `trade_buy_button`, `trade_sell_button` (ржавая кнопка SoC,
оранжевая надпись). Всё остальное в `actor_menu.xml` не тронуто (инвентарь, обыск, улучшения выглядят как раньше), для 4:3 есть `actor_menu_4x3.xml`.
Чего движок не даёт: раскладки SoC (панель описания по центру, два маленьких списка, одна кнопка «Торговать»), панелей персонажей и денег (общие с инвентарём, поэтому верхняя полоса и центр остались
прежними), заголовков «Вещи Меченого» / «Рюкзак». Текстуры и оригинальное оформление принадлежат GSC Game World, всё вырезано из оригинальных листов SoC (один файл 1 МБ). Необязательный вариант
`optional/soc_trade_top` перекрашивает и верхние полосы, но зависит от порядка отрисовки движка, нужен один тест.
