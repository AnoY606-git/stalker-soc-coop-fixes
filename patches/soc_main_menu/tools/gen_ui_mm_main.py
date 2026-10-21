"""Builds configs\\ui\\ui_mm_main.xml and configs\\misc\\socfx_mm.ltx for one main menu style.

Usage: python gen_ui_mm_main.py <mod ui_mm_main.xml> <out gamedata dir> <style>
  style = soc     the original SoC art: wall picture, SoC sky video, fire video, shutters, selector bar (the first version)
          ue4_a   the UE4 remake video (S.T.A.L.K.E.R. UE4 main menu by Daniel Swahn / Ivan Sorce) + the SoC shutter panel and selector
                  bar on the planks at the right
          ue4_b   the UE4 remake video, no panel, light graffiti text buttons on the dark planks, a small selector bar

Buttons: every page and every button (window_name, caption string) is read from the mod's own ui_mm_main.xml, so nothing the
menu script needs (btn_net_game, btn_options, btn_credits, btn_quit, btn_multiplayer, btn_logout, btn_ret, btn_lastsave, btn_save,
btn_quit_to_mm, btn_internet, btn_localnet, btn_new_back) can disappear. Only the geometry / style changes.

Layout: the xrMPE main menu works in a 1080 high space; the SoC menu was drawn for 1024x768, so every SoC number is multiplied
by S = 1080 / 768 = 1.40625. The UE4 video is 1920x1080 (16:9): the numbers below for ue4_* are positions inside that picture
(scripts\\socfx_mm_selector.script moves everything when the screen is not 16:9, keeping the whole picture visible).
"""
import os
import sys
import xml.etree.ElementTree as ET

S = 1080.0 / 768.0
src, outdir, STYLE = sys.argv[1], sys.argv[2], sys.argv[3]
assert STYLE in ('soc', 'ue4_a', 'ue4_b')


def n(v):
    return int(round(v * S))


# ---- SoC geometry (1024x768 units) --------------------------------------------------------------------------------------
ART = (0, 0, 1024, 768)
MOVIE = (148, 0, 876, 400)        # back_movie
FIRE = (525, 459, 128, 256)       # fire_movie
WND = (590, 586 / S, 392, 280)    # shniaga_wnd: top = 586 in 1080 space, the first shutter of the picture

# ---- UE4 layouts, in the 1920x1080 picture --------------------------------------------------------------------------------
PANEL_W, PANEL_H = n(217), n(360)      # SoC shutter panel cut out of the SoC sheet (textures\\ui\\socfx_ue4_panel.dds, 217x360)
PANEL_ROW0 = n(419 - 345)              # first shutter below the top of the cut out
PANEL_COL = n(782 - 678) - PANEL_W / 2.0   # buttons column centre relative to the panel centre (SoC buttons are at x=782)
UE4 = {
    # col_cx / row0_y: centre of the button column and top of the first button; bar_f: size of the selector
    'ue4_a': dict(col_cx=1640 + PANEL_COL, row0_y=730 - PANEL_H / 2.0 + PANEL_ROW0, bar_f=0.65, panel_cx=1640, panel_cy=730),
    'ue4_b': dict(col_cx=1700, row0_y=560, bar_f=0.5),
}


def center(rect):
    """centre of an SoC rect relative to the centre of the 1024x768 art, in 1080-space"""
    x, y, w, h = rect
    return n(x + w / 2.0 - 512), n(y + h / 2.0 - 384)


def mid_static(rect, tex, extra=''):
    cx, cy = center(rect)
    return ('\t\t<auto_static anchor="mid-center" x="%d" y="%d" width="%d" height="%d" stretch="1">\n'
            '\t\t\t<texture%s>%s</texture>\n\t\t</auto_static>\n') % (cx, cy, n(rect[2]), n(rect[3]), extra, tex)


tree = ET.parse(src)
pages = []
for page in tree.getroot():
    if page.tag.startswith('menu_') and page.tag != 'menu_sound':
        btns = []
        for b in page.findall('btn'):
            btns.append((b.findtext('window_name'), b.find('text').text, b.find('text').get('font')))
        pages.append((page.tag, btns))
sound = tree.getroot().find('menu_sound')
music = sound.findtext('menu_music')

BW, BH = n(392), 49      # button = the whole bar width; 49 = pitch of the shutters of the picture (SoC rows were 30 x 1.40625 = 42 and drifted off them)
BAR_F = 0.65 if STYLE in ('soc', 'ue4_a') else UE4['ue4_b']['bar_f']   # selector size, same numbers as bar_f in the ltx
out = ['<w>\n']
if STYLE == 'soc':
    out.append('\t<background anchor="fullscreen">\n')
    # 1. black fill (covers ultra wide screens), 2. movie, 3. art with a hole for the movie, 4. fire movie, 5. side strips
    out.append('\t\t<auto_static anchor="mid-center" x="0" y="0" width="4400" height="1080" stretch="1">\n'
               '\t\t\t<texture>socfx_mm_black</texture>\n\t\t</auto_static>\n')
    out.append(mid_static(MOVIE, 'ui\\socfx_mm_back', ' x="0" y="0" width="876" height="400"'))
    out.append(mid_static(ART, 'socfx_mm_bg'))
    out.append(mid_static(FIRE, 'ui\\socfx_mm_fire'))
    out.append('\t\t<auto_static anchor="mid-center" x="%d" y="0" width="%d" height="1080" stretch="1">\n'
               '\t\t\t<texture>socfx_mm_left</texture>\n\t\t</auto_static>\n' % (-(n(512) + n(200)), n(400)))
    out.append('\t\t<auto_static anchor="mid-center" x="%d" y="0" width="%d" height="1080" stretch="1">\n'
               '\t\t\t<texture>socfx_mm_right</texture>\n\t\t</auto_static>\n' % (n(512) + n(200), n(400)))
    out.append('\t</background>\n\n')
    wx, wy = center(WND)
    wanchor = 'mid-center'
else:
    # the script needs a node called background; the picture itself is made by the script (statics socfx_ue4_*), below the buttons
    out.append('\t<background anchor="fullscreen">\n\t\t<auto_static anchor="mid-center" x="0" y="0" width="4" height="4" stretch="1">\n'
               '\t\t\t<texture>socfx_mm_btn_e</texture>\n\t\t</auto_static>\n\t</background>\n\n')
    out.append('\t<socfx_ue4_black x="0" y="0" width="1920" height="1080" stretch="1">\n\t\t<texture>socfx_mm_black</texture>\n\t</socfx_ue4_black>\n')
    out.append('\t<socfx_ue4_video x="0" y="0" width="1920" height="1080" stretch="1">\n\t\t<texture width="1280" height="720">ui\\socfx_ue4_menu</texture>\n\t</socfx_ue4_video>\n')
    if STYLE == 'ue4_a':
        out.append('\t<socfx_ue4_panel x="0" y="0" width="%d" height="%d" stretch="1">\n\t\t<texture>socfx_ue4_panel</texture>\n\t</socfx_ue4_panel>\n'
                   % (PANEL_W, PANEL_H))
    out.append('\n')
    u = UE4[STYLE]
    # anchor mid-right: x = distance from the screen's right edge to the window's right edge, y = centre of the window from the
    # screen centre. The buttons keep their place at the right edge on every screen; the script puts the picture and the panel
    # around them (moving the button window from the script does not move its buttons).
    wanchor = 'mid-right'
    wx, wy = int(round(1920 - (u['col_cx'] + BW / 2.0))), int(round(u['row0_y'] + n(280) / 2.0 - 540))

# shniaga window (the buttons): written as an anchored window, x / y from the screen centre
out.append('\t<shniaga_wnd anchor="%s" x="%d" y="%d" width="%d" height="%d">\n' % (wanchor, wx, wy, BW, n(280)))
out.append('\t\t<buttons_region x="0" y="0" width="%d" height="%d"/>\n' % (BW, n(280)))
out.append('\t</shniaga_wnd>\n\n')

# statics of the Lua selector bar (scripts\\socfx_mm_selector.script moves them; the positions here are placeholders).
# The engine ignores a <shniaga> bar in this xml (tried), so the bar is built by the script.
def sel(name, w, h, tex):
    return ('\t<%s x="0" y="0" width="%d" height="%d" stretch="1">\n\t\t<texture>%s</texture>\n\t</%s>\n'
            % (name, int(round(n(w) * BAR_F)), int(round(n(h) * BAR_F)), tex, name))


out.append(sel('socfx_bar', 392, 73, 'socfx_mm_move'))
out.append(sel('socfx_roll_l', 55, 55, 'socfx_mm_roll_L_01'))
out.append(sel('socfx_roll_r', 55, 55, 'socfx_mm_roll_R_01'))
out.append(sel('socfx_grating_l', 55, 67, 'socfx_mm_grating_l'))
out.append(sel('socfx_grating_r', 55, 67, 'socfx_mm_grating_r'))
out.append('\n')

if STYLE == 'ue4_b':
    colors = ('<e color="ui_white"/>', '<t color="ui_white"/>', '<d color="dark_gray"/>', '<h color="ui_white"/>')
else:
    colors = ('<e color="ui_black"/>', '<t color="ui_black"/>', '<d color="dark_gray"/>', '<h color="ui_black"/>')
for tag, btns in pages:
    out.append('\t<%s>\n' % tag)
    for i, (wname, caption, font) in enumerate(btns):
        out.append(
            '\t\t<btn x="0" y="%d" width="%d" height="%d" stretch="1">\n'
            '\t\t\t<window_name>%s</window_name>\n'
            '\t\t\t<texture>socfx_mm_btn</texture>\n'
            '\t\t\t<text font="graffiti22" align="c" vert_align="c">%s</text>\n'
            '\t\t\t<text_color>\n'
            '\t\t\t\t%s\n\t\t\t\t%s\n\t\t\t\t%s\n\t\t\t\t%s\n'
            '\t\t\t</text_color>\n'
            '\t\t\t<sound_h>interface\\selector_button</sound_h>\n'
            '\t\t\t<sound_t>interface\\select_button</sound_t>\n'
            '\t\t</btn>\n' % ((i * BH, BW, BH, wname, caption) + colors))
    out.append('\t</%s>\n\n' % tag)

out.append('\t<menu_sound random="0">\n\t\t<menu_music>%s</menu_music>\n\t</menu_sound>\n\n' % music)
out.append('\t<static_version anchor="bot-left" x="21" y="20" width="400" height="40">\n'
           '\t\t<text font="graffiti19" color="gray_mpe" vert_align="b" align="l"/>\n'
           '\t</static_version>\n')
out.append('</w>\n')

os.makedirs(os.path.join(outdir, 'configs', 'ui'), exist_ok=True)
os.makedirs(os.path.join(outdir, 'configs', 'misc'), exist_ok=True)
open(os.path.join(outdir, 'configs', 'ui', 'ui_mm_main.xml'), 'w', encoding='utf-8', newline='\r\n').write(''.join(out))

ltx = ['; Main menu style of the SoC main menu patch (soc_main_menu). Written by tools\\gen_ui_mm_main.py together with',
       '; configs\\ui\\ui_mm_main.xml: the two files belong together (the buttons are in the xml, the engine reads them from there).',
       '; soc = original SoC art, ue4_a = UE4 remake picture + SoC shutter panel, ue4_b = UE4 remake picture + light text buttons.',
       '; Numbers for ue4_*: positions in the 1920x1080 picture (centre of the button column, top of the first button, size of',
       '; the selector bar, centre of the shutter panel).', '[menu]', 'style = %s' % STYLE]
if STYLE != 'soc':
    u = UE4[STYLE]
    for key in ('col_cx', 'row0_y', 'bar_f', 'panel_cx', 'panel_cy'):
        if key in u:
            ltx.append('%s = %s' % (key, ('%.2f' % u[key]).rstrip('0').rstrip('.')))
    if STYLE == 'ue4_a':
        ltx.append('panel_w = %d' % PANEL_W)
        ltx.append('panel_h = %d' % PANEL_H)
open(os.path.join(outdir, 'configs', 'misc', 'socfx_mm.ltx'), 'w', encoding='ascii', newline='\r\n').write('\n'.join(ltx) + '\n')
print('style', STYLE, 'pages:', ', '.join('%s(%d)' % (t, len(b)) for t, b in pages))
