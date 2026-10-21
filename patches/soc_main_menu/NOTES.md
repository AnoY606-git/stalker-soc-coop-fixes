# SoC main menu - notes

FOSTER asked for the main menu of Shadow of Chernobyl. What he means is the UE4 remake of the SoC menu scene (the video with the brick wall
S.T.A.L.K.E.R., the campfire and the burning Chernobyl power plant), so that video is the background now. The menu is shipped in three
switchable styles; the default is `ue4_b`. (`patches\soc_music` already restored the SoC menu music.)

## Credits
- The background video is from the "S.T.A.L.K.E.R. UE4 main menu" (Unreal Engine 4 remake of the SoC menu scene) by **Daniel Swahn** and
  **Ivan Sorce**. It is used here with the author's permission. The UE4 logo and the "S.T.A.L.K.E.R. SoC Remake" badge that were burned into the
  clip were removed (inpainted) for this mod; everything else in the picture is the authors' work.
- The original SoC art (wall sheet, gears, bar, sky and fire videos, used by the `soc` style and for the panel of `ue4_a`) is from GSC Game World's
  S.T.A.L.K.E.R.: Shadow of Chernobyl.

## The three styles
| style | what you see | where it lives |
|---|---|---|
| `ue4_b` (DEFAULT) | UE4 video full screen, no panel: light graffiti text buttons on the dark planks at the right, a small selector bar (metal bar, glass, gears, gratings, 0.5 size, stretched to 420 wide so the gears stay off the longest caption, `bar_w` in the ltx; checked 2026-10-21 at 800x600 and 1280x720 with the bar on RETURN TO GAME and EXIT THE GAME: `tests\ue4b_*_mm_row0.jpg`, `tests\ue4b_*_coop_row6.jpg`) that glides to the button under the mouse | `gamedata\configs\ui\ui_mm_main.xml` + `configs\misc\socfx_mm.ltx` of this patch |
| `ue4_a` | UE4 video full screen + the SoC shutter panel (metal plates, cut out of the SoC sheet) on the planks at the right, black graffiti text on the plates, the SoC sized selector bar (0.65) | `optional\mm_style_ue4_a\gamedata` |
| `soc` | the first version: the original SoC menu (wall picture, SoC sky and fire videos, shutters, side strips), no UE4 video | `optional\mm_style_soc\gamedata` (also ships the SoC only sky / fire videos) |

Why `ue4_b` is the default: the point of the UE4 menu is its picture. Style A lays a big grey panel over the planks and hides the right fifth of
the scene, and the SoC plates (flat 2005 art) clash a little with the UE4 render. Style B keeps every pixel of the video visible, reads well on
the dark planks at 16:9 and 4:3 (white text with a dark vignette behind it), and still has the SoC selector bar. A and the SoC version stay one flag away.

Switching (the xml and the ltx always belong together, the buttons are in the xml, `scripts\socfx_mm_selector.script` reads the numbers from the ltx):
- Build time: `python build.py <out.db> --mm-style=ue4_a` (or `--mm-style=soc`); the optional folder is laid over the default files.
  `--mm-style=ue4_b` is accepted and changes nothing (it is the default).
- By hand: copy `optional\mm_style_<name>\gamedata\*` over `gamedata` (a second small db or a loose gamedata folder loads the same way).
- `tools\gen_styles.py <default style>` regenerates every style (xml + ltx + the optional folders) from the mod's own `ui_mm_main.xml`;
  `tools\gen_ui_mm_main.py` makes one style.

All styles keep the same pages and the same button and window names as the xrMPE / Shadow of COOP menu, taken from the mod's own `ui_mm_main.xml`:
`menu_main` (btn_net_game = Play, btn_options, btn_credits, btn_quit), `menu_main_logout`, `menu_main_mm`, `menu_main_coop_mm` (the in-game ESC menu:
btn_ret, btn_lastsave, btn_save, btn_options, btn_credits, btn_quit_to_mm, btn_quit), `menu_network_game` (btn_internet, btn_localnet, btn_new_back),
plus btn_multiplayer and btn_logout. Strings, sounds and the menu music are unchanged. The Options / Load / Multiplayer dialogs are the mod's own.

## The video
- `gamedata\textures\ui\socfx_ue4_menu.ogm`: Theora, 1280x720, 20 fps, no audio, 19.4 s, 3.7 MB (budget about 6 MB), the whole db of this patch is about 4.2 MB.
  The engine plays `.ogm` in a static (`<texture width="1280" height="720">ui\socfx_ue4_menu</texture>`) and loops it.
- Source: the 1080p SD-patched clip (`composite_sd.py`: the UE4 logo on the wall and the corner badge replaced by Stable Diffusion patches,
  brightness matched per frame so the campfire flicker carries over). It was chosen over the cleaned clip `mainmenu_final_1080p.mp4` (LaMa inpaint,
  cropped and zoomed in to push the badge out of the frame): the SD clip keeps the full picture (the backpack, rifle, ammo box and the roof at the left
  stay in the frame, which the wide 16:9 layout needs) and the wall is clean where the "U" was in both clips. Checked in several frames across the clip.
- Seamless loop: `tools\make_ue4_loop.py` cross fades the last 0.5 s of the clip into its first 0.5 s (the loop is shorter by that), so the wrap
  last frame -> first frame is two consecutive source frames. Measured on the decoded .ogm: blurred difference across the wrap 0.8 grey levels
  (the source clip's own end-to-start jump was 2.6 raw), no visible jump. The encode is done with Blender 4.2 (headless): the ffmpeg 8.0.1 on the dev PC
  writes corrupt Theora packets that the engine shows as growing blocky garbage; the script checks that ffmpeg decodes the result without messages.
- Rebuild: `python tools\make_ue4_loop.py <1080p mp4> textures\ui\socfx_ue4_menu.ogm 1280 20 0.5 2000` (needs numpy, opencv-python, ffmpeg, Blender 4.2).
- Layout: the video is always shown whole (fitted to the screen: black bars at the sides on wider screens, above and below at 4:3). The buttons are
  anchored to the right screen edge at a fixed place inside the 1920x1080 picture, so they sit on the planks at 16:9; at 4:3 the picture is
  scaled to the screen width and the buttons move with it.

## How the menu works here
- Drawn by xrMPE script + xml: `scripts\ui_main_menu.script` (the mod's copy minus the "buy STALKER games" news block, plus a block at the end,
  `tools\hooks_append.lua`, that creates the picture and the selector and feeds it the mouse; it is the only patch that ships this file) builds
  `configs\ui\ui_mm_main.xml`. The Windows rects, `SetWndPos` and the mouse are real screen pixels, the xml works in a 1080 high space.
- The engine ignores a `<shniaga>` bar in this xml, so `scripts\socfx_mm_selector.script` builds the selector from plain statics (bar, two gears with 20 frames,
  two gratings), moves them to the row under the mouse at the SoC speed, hides them with the menu buttons, and places the video (and the A panel)
  below the buttons. Everything is in pcall: on any error the menu still works, only the picture or the bar is missing.
- The SoC "magnifier" (the glass enlarges the button text) is a special engine render pass and is not ported (the glass is a flat pane).
- Original SoC menu data (Steam SoC 1.0006) was read with a reader written for this task (the SoC archives have an obfuscated index; key parameters from the open XRay 1.0006 sources).
  `gamedata\textures\ui\socfx_mm_sheet.dds` = the SoC `ui_mainmenu.dds`; ids renamed `ui_menu_*` -> `socfx_mm_*` (`tools\gen_textures_descr.py`) so nothing of CoP / xrMPE is touched.
- Mod logo and "OPEN BETA TEST" label are gone (the picture says S.T.A.L.K.E.R. Shadow of Chernobyl).

## Test (automated, Cordon, one client, `tests\`)
- `tests\mm_screenshot_hook.lua` opens the menu with `main_menu on`; `tests\menu_pages_test_only.lua` (TEST ONLY, appended to the script of a throw-away stage built by
  `build.py --stage`) moves the bar with a simulated mouse and switches through all five pages, asking the harness for an engine screenshot of each.
- 800x600 (4:3) and 1280x720 (16:9, `-Cfg vid=1280x720`): all pages show all their buttons, the bar sits over the chosen row, the video plays, the client log has no
  missing texture / xml / script error. Screenshots in `tests\`: `ue4b_*` (default style), `ue4a_*` (panel), `soc_style_*` (SoC art), each
  `<style>_<4x3_800x600|16x9_1280x720>_<page>_row<n>.jpg`. `tests\reference\` has frames of the sources.
- The bar following a real mouse is not driven by the harness (simulated mouse move in the script, same pixel units); no human played with a real mouse.

## Кратко (RU)
Фон главного меню: видео из UE4-ремейка меню ТЧ (авторы Daniel Swahn и Ivan Sorce, используется с разрешения автора; логотипы UE4 и «SoC Remake»
убраны). Видео зациклено без шва (кросс-фейд 0,5 с), Theora 1280x720, 3,7 МБ, на весь экран, сохраняет пропорции в 4:3 и 16:9. Три стиля:
`ue4_b` (по умолчанию: светлые текстовые кнопки на досках справа, маленькая планка выбора с шестерёнками), `ue4_a` (то же видео + металлическая панель
с шторками ТЧ), `soc` (первая версия, оригинальное меню ТЧ). Переключение: `build.py --mm-style=ue4_a` или `--mm-style=soc`, либо скопировать
`optional\mm_style_<имя>\gamedata` поверх `gamedata`. Все кнопки и имена окон xrMPE на месте. Оригинальные материалы ТЧ принадлежат GSC Game World.
