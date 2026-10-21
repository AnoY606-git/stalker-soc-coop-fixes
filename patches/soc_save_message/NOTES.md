# Save message at the bottom of the screen (like Shadow of Chernobyl)

Requested by FOSTER (maintainer of Shadow of COOP 8.1): "Move the save message lower so it is like the original." The text "Game saved: quicksave - 3"
showed in the middle of the screen, just under the crosshair (about 69% of the height at 1920x1080).

## Cause
The message is shown by the engine (not by a script: no script in the mod or in xrMPE adds the `game_saved` / `autosave` static), as the custom static `game_saved`
of `configs\ui\ui_custom_msgs.xml`. Three versions of that node exist:
- Steam SoC 1.0006: `x=100 y=730 width=800 height=30` in the 1024x768 UI, i.e. the box starts at 95% of the height, centered, `graffiti22`, colour 240/217/182.
  `autosave` is at `y=700` (91%).
- xrMPE base (`xrmpe_patch`): `anchor="bot-center" x="0" y="27"`, already at the bottom.
- The mod's `gamedata.db0` copy (the one that wins, add-on files are mounted after the base): `x=184 y=730` copied unchanged from the 1024x768 SoC numbers into the
  1920x1080 layout, so 730 is 68% of the height. `autosave` has the same numbers.

## What it does
Ships the mod's `ui_custom_msgs.xml` byte for byte except two nodes, both now anchored to the bottom of the screen so they follow any resolution and aspect ratio:
- `game_saved`: `anchor="bot-center" x="0" y="11"` (box height 42, so its top is at 95% of a 1080-high screen, the same place as SoC's box).
- `autosave`: `anchor="bot-center" x="0" y="54"` (top at 91%, like SoC's `y=700` above the save message).
Font (`graffiti22`), colour (240/217/182/255), width, height and the 3 s lifetime already match SoC and are not touched. There is no 4:3 variant of this file in the
mod or in xrMPE (the base game only has `ui_custom_msgs.xml`), so the anchor is what keeps it at the bottom on 4:3 too.

## Checked in game (2026-10-21, 800x600 lobby, patch loaded)
The real `save quicksave - N` message is drawn centred at about 96% of the height and the autosave line at about 93%, so the anchors work for this
static (the mod's own file with `y=730` in the 1920x1080 space put it at 68%, which is what FOSTER saw; no other file in the mod or xrMPE overrides it).
A script-side `GetWndPos` on the static reports `y=6` because it leaves the anchor offset out (11 * 600/1080); that number is not where the text is drawn.

## Files (one patch per file: no other patch ships `ui_custom_msgs.xml`)
- `gamedata/configs/ui/ui_custom_msgs.xml`

## Offline checks done
`diff` against the mod's source file (only the two nodes above differ), XML parses (comments stripped first, the source carries `--` inside comments),
`tools/check_conflicts.py` (no new conflicts), `build.py ... --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing` BUDGET OK (headroom 22.6 MB),
stage copy identical to the patch file. Not seen in game (offline task).

## Test plan
`tests/save_message_hook.lua` (command in the file header, one listen host): fills the same `game_saved` static by script, then `autosave`, then makes a real
server save, taking an engine screenshot of each (`svmsg_<mode>_static`, `_autosave`, `_real`), and asserts the static window's bottom edge is in the bottom 12%
of the screen. Run it twice (800x600 and `-Cfg vid=1920x1080`) and compare the shots with FOSTER's screenshot: the text must sit near the bottom edge, centered.

## RU
Сообщение «Игра сохранена: quicksave - N» показывалось посередине экрана, под прицелом (около 69% высоты при 1920x1080). ФОСТЕР просил опустить его, как в оригинале.
Сообщение рисует движок (скриптов, которые добавляют `game_saved` / `autosave`, нет), положение задаёт `configs\ui\ui_custom_msgs.xml`. В оригинальной ТЧ рамка начинается
на 95% высоты (`y=730` из 768), в xrMPE она уже внизу (`anchor="bot-center"`), а в файле мода числа ТЧ (`y=730`) перенесены в раскладку 1920x1080 как есть, поэтому текст оказался
на 68%. Патч привязывает `game_saved` (`y=11`, верх на 95%) и `autosave` (`y=54`, на 91%, как `y=700` в ТЧ) к низу экрана; шрифт, цвет и размеры уже как в ТЧ. Файл
остальным байт в байт как в моде. Тест: `tests/save_message_hook.lua`.
