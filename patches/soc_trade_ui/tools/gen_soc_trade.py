#!/usr/bin/env python3
"""Builds the art and the xml of patch soc_trade_ui from the ORIGINAL Shadow of Chernobyl sheets (GSC Game World).

Inputs (read only):
  --soc-inv2    SoC textures\\ui\\ui_inventory2.dds   (rust panels; read with patches\\soc_main_menu\\tools-style xdb_soc.py)
  --soc-common  SoC textures\\ui\\ui_common.dds       (the rust button ui_button_main01_*)
  --mod-xml     Shadow of COOP actor_menu.xml          (16:9, db0 of the add-on)
  --base-xml43  xrMPE actor_menu_4x3.xml               (4:3, base patch)
Outputs (default: the patch folder next to this tools folder):
  gamedata\\textures\\ui\\ui_soc_trade.dds              1024x1024 DXT5 atlas
  gamedata\\configs\\ui\\textures_descr\\ui_soc_trade.xml
  gamedata\\configs\\ui\\actor_menu.xml, actor_menu_4x3.xml     (only trade-only nodes are edited)
  optional\\soc_trade_top\\gamedata\\configs\\ui\\actor_menu.xml, actor_menu_4x3.xml   (variant: top panels skinned too)

What is edited in the two xml files (everything else is byte for byte the source file):
  left_delimiter, right_delimiter  (shown by the engine in trade mode only): texture, rect, children font/colour/position
  trade_buy_button, trade_sell_button (trade only): texture, text font, text colours
Positions of every visible element (lists, buttons, prices, names, money, weights) stay where they were.

python gen_soc_trade.py --soc-inv2 <dds> --soc-common <dds> --mod-xml <xml> --base-xml43 <xml> [--out <patch dir>] [--preview <png dir>]
"""
import argparse, os, re, sys
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('--soc-inv2', required=True)
ap.add_argument('--soc-common', required=True)
ap.add_argument('--mod-xml', required=True)
ap.add_argument('--base-xml43', required=True)
ap.add_argument('--out', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument('--preview', default=None)
A = ap.parse_args()

INV = Image.open(A.soc_inv2).convert('RGBA')
COM = Image.open(A.soc_common).convert('RGBA')
BG = (36, 40, 42)          # opaque colour under the translucent SoC panel interior (keeps the old Gunslinger art from showing through)
GAP = (10, 11, 12, 255)    # colour between the panels
SC = 0.75                  # atlas pixels per UI unit


def over(img, rgb):
    b = Image.new('RGBA', img.size, rgb + (255,))
    b.alpha_composite(img)
    return b


def rs(img, w, h):
    return img.resize((max(1, int(round(w))), max(1, int(round(h)))), Image.LANCZOS)


def darken(img, f):
    r, g, b, a = img.split()
    r = r.point(lambda v: int(v * f)); g = g.point(lambda v: int(v * f)); b = b.point(lambda v: int(v * f))
    return Image.merge('RGBA', (r, g, b, a))


# ---- SoC pieces (pixel boxes in ui_inventory2.dds) ---------------------------------------------------------------
# the lower centre panel (343..680 x 488..698): rust bar on the left, thin edges right and bottom, dirty dark interior
SRC_DIRT = (380, 530, 665, 680)
SRC_BAR = (343, 520, 362, 640)
SRC_TL = (343, 488, 372, 518)
SRC_BL = (343, 640, 362, 698)
SRC_TOP = (372, 489, 668, 514)
SRC_TR = (668, 488, 680, 514)
SRC_RIGHT = (672, 514, 680, 692)
SRC_BOT = (362, 692, 672, 698)
SRC_BR = (672, 692, 680, 698)
# the metal band over the upper centre panel (355..680 x 255..284): used for the price / weight rails
SRC_BAND = (352, 255, 676, 284)


def crop(box):
    return INV.crop(box)


def panel(w, h):
    """Thin rust panel w x h (UI units, opaque)."""
    k = 0.8                     # SoC pixels -> UI units for the frame parts (thin, so the first list cell is not covered)
    bw = int(round(19 * k)); rw = 6; bh = 5; th = 12
    tlw, tlh = int(round(29 * k)), int(round(30 * k))
    blh = int(round(58 * k))
    can = rs(over(crop(SRC_DIRT), BG), w, h)
    can.paste(rs(crop(SRC_BAR), bw, h - tlh - blh), (0, tlh))
    can.paste(rs(crop(SRC_TL), tlw, tlh), (0, 0))
    can.paste(rs(crop(SRC_BL), bw, blh), (0, h - blh))
    can.paste(rs(over(crop(SRC_TOP), BG), w - tlw - rw, th), (tlw, 0))
    can.paste(rs(crop(SRC_TR), rw, th), (w - rw, 0))
    can.paste(rs(crop(SRC_RIGHT), rw, h - th - bh), (w - rw, th))
    can.paste(rs(crop(SRC_BOT), w - bw - rw, bh), (bw, h - bh))
    can.paste(rs(crop(SRC_BR), rw, bh), (w - rw, h - bh))
    return can


def strip(w, h):
    """Metal rail w x h with the two screws of the SoC header band kept at the ends."""
    src = darken(crop(SRC_BAND), 0.62)
    cap = 16
    f = h / float(src.height)
    cw = int(round(cap * f))
    out = Image.new('RGBA', (w, h))
    out.paste(rs(src.crop((0, 0, cap, src.height)), cw, h), (0, 0))
    out.paste(rs(src.crop((cap, 0, src.width - cap, src.height)), w - 2 * cw, h), (cw, 0))
    out.paste(rs(src.crop((src.width - cap, 0, src.width, src.height)), cw, h), (w - cw, 0))
    return out


def column(w, h, rects, top_rect=None):
    """One full-height trade column (UI units): dark ground + panels. rects = dict name -> (x, y, w, h)."""
    can = Image.new('RGBA', (w, h), GAP)
    for name, (x, y, pw, ph) in rects.items():
        can.paste(strip(pw, ph) if name.startswith('strip') else panel(pw, ph), (x, y))
    return can


# ---- layouts (UI units of each xml: 16:9 1920x1080, 4:3 1280x900) --------------------------------------------------
WIDE = dict(w=704, h=1080, y0=148,
            rects={'top': (14, 6, 676, 136), 'A': (14, 148, 676, 256), 'strip1': (14, 408, 676, 56), 'B': (14, 468, 676, 546),
                   'strip2': (14, 1018, 676, 44)})
N43 = dict(w=428, h=900, y0=124,
           rects={'top': (8, 4, 412, 116), 'A': (8, 124, 412, 214), 'strip1': (8, 340, 412, 52), 'B': (8, 394, 412, 444),
                  'strip2': (8, 846, 412, 40)})

wide = column(WIDE['w'], WIDE['h'], WIDE['rects'])
n43 = column(N43['w'], N43['h'], N43['rects'])

# buttons: SoC ui_button_main01 (157x48): rust frame with the gear teeth; caps kept, middle stretched
BTN = {'d': (0, 422), 'e': (0, 470), 't': (0, 518), 'h': (0, 566)}


def button(state, w, h):
    x, y = BTN[state]
    src = COM.crop((x, y, x + 157, y + 48))
    cap = 24
    f = h / 48.0
    cw = int(round(cap * f))
    out = Image.new('RGBA', (w, h))
    out.paste(rs(src.crop((0, 0, cap, 48)), cw, h), (0, 0))
    out.paste(rs(src.crop((cap, 0, 157 - cap, 48)), w - 2 * cw, h), (cw, 0))
    out.paste(rs(src.crop((157 - cap, 0, 157, 48)), cw, h), (w - cw, 0))
    return out


# ---- atlas -------------------------------------------------------------------------------------------------------
ATL = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
wide_s = rs(wide, wide.width * SC, wide.height * SC)      # 528 x 810
n43_s = rs(n43, n43.width * SC, n43.height * SC)           # 321 x 675
ATL.paste(wide_s, (0, 0))
X43 = wide_s.width
ATL.paste(n43_s, (X43, 0))
XB = X43 + n43_s.width
BW, BH = 152, 28
for i, s in enumerate('ehtd'):
    ATL.paste(rs(button(s, 201, 37), BW, BH), (XB, i * 30))

out = A.out
tex = os.path.join(out, 'gamedata', 'textures', 'ui')
os.makedirs(tex, exist_ok=True)
ATL.save(os.path.join(tex, 'ui_soc_trade.dds'), pixel_format='DXT5')

y0w = int(round(WIDE['y0'] * SC)); y0n = int(round(N43['y0'] * SC))
descr = f'''<w>
	<!-- Shadow of Chernobyl trade skin. Art: GSC Game World (S.T.A.L.K.E.R.: Shadow of Chernobyl), recomposed by tools/gen_soc_trade.py -->
	<file name="ui\\ui_soc_trade">
		<texture id="ui_soc_trade_col_wide_full" x="0" y="0" width="{wide_s.width}" height="{wide_s.height}" />
		<texture id="ui_soc_trade_col_wide" x="0" y="{y0w}" width="{wide_s.width}" height="{wide_s.height - y0w}" />
		<texture id="ui_soc_trade_col_4x3_full" x="{X43}" y="0" width="{n43_s.width}" height="{n43_s.height}" />
		<texture id="ui_soc_trade_col_4x3" x="{X43}" y="{y0n}" width="{n43_s.width}" height="{n43_s.height - y0n}" />
		<texture id="ui_soc_trade_btn_e" x="{XB}" y="0" width="{BW}" height="{BH}" />
		<texture id="ui_soc_trade_btn_t" x="{XB}" y="60" width="{BW}" height="{BH}" />
		<texture id="ui_soc_trade_btn_d" x="{XB}" y="90" width="{BW}" height="{BH}" />
		<texture id="ui_soc_trade_btn_h" x="{XB}" y="30" width="{BW}" height="{BH}" />
	</file>
</w>
'''
dd = os.path.join(out, 'gamedata', 'configs', 'ui', 'textures_descr')
os.makedirs(dd, exist_ok=True)
open(os.path.join(dd, 'ui_soc_trade.xml'), 'w', encoding='utf-8', newline='\n').write(descr)

# ---- xml ---------------------------------------------------------------------------------------------------------
BTN_TEXT = ('<text_color>\n\t\t\t<e color="ui_7"/>\n\t\t\t<t color="ui_black"/>\n'
            '\t\t\t<d color="ui_5"/>\n\t\t\t<h color="ui_black"/>\n\t\t</text_color>')


def read(p):
    return open(p, 'rb').read().decode('utf-8')


def sub_block(xml, tag, fn):
    """Replace the first <tag ...> ... </tag> block by fn(block)."""
    m = re.search(r'<%s\b.*?</%s>' % (tag, tag), xml, re.S)
    if not m:
        raise SystemExit('node %s not found' % tag)
    return xml[:m.start()] + fn(m.group(0)) + xml[m.end():]


def make_delim(block, tex_id, new_y, dy, font, new_h):
    """block: one delimiter node. Re-texture, move the rect (top edge to new_y, bottom edge unchanged) and shift the children by dy."""
    m = re.match(r'<(\w+)\s+x="([\d.]+)"\s+y="([\d.]+)"\s+width="([\d.]+)"\s+height="([\d.]+)"', block)
    name, x, y, w, h = m.group(1), m.group(2), float(m.group(3)), m.group(4), float(m.group(5))
    head = '<%s x="%s" y="%d" width="%s" height="%d"' % (name, x, new_y, w, new_h)
    block = head + block[m.end():]
    block = re.sub(r'<texture>[^<]*</texture>', '<texture>%s</texture>' % tex_id, block, 1)

    def child(mc):
        cy = float(mc.group(2)) + dy
        return '%s%s' % (mc.group(1), ('%g' % cy))
    block = re.sub(r'(<trade_\w+ x="[\d.]+" y=")([\d.]+)', child, block)
    # SoC colours / fonts on the three texts (caption dim cream, price cream, weight limit dim)
    block = re.sub(r'(<trade_caption[^>]*>\s*<text [^>]*?)font="[^"]*" color="[^"]*"', r'\1font="%s" color="ui_8"' % font, block)
    block = re.sub(r'(<trade_price[^>]*>\s*<text [^>]*?)font="[^"]*"', r'\1font="%s" color="ui_6"' % font, block)
    block = re.sub(r'(<trade_weight_max[^>]*>\s*<text [^>]*?)font="[^"]*" color="[^"]*"', r'\1font="%s" color="ui_8"' % font, block)
    return block


def make_button(block, big_font=None):
    block = re.sub(r'<texture>[^<]*</texture>', '<texture>ui_soc_trade_btn</texture>', block, 1)
    block = re.sub(r'<text font="[^"]*"', '<text font="graffiti22"', block, 1)
    block = re.sub(r'<text_color>.*?</text_color>', BTN_TEXT, block, 1, flags=re.S)
    return block


def build_xml(src, wide_layout, top_skin):
    L = WIDE if wide_layout else N43
    tid = ('ui_soc_trade_col_wide' if wide_layout else 'ui_soc_trade_col_4x3') + ('_full' if top_skin else '')
    new_y = 0 if top_skin else L['y0']
    font = 'letterica18' if wide_layout else 'letterica16'
    xml = src
    for tag in ('left_delimiter', 'right_delimiter'):
        def f(block, tag=tag):
            m = re.match(r'<\w+\s+x="[\d.]+"\s+y="([\d.]+)"', block)
            old_y = float(m.group(1))
            return make_delim(block, tid, new_y, old_y - new_y, font, L['h'] - new_y)
        xml = sub_block(xml, tag, f)
    xml = sub_block(xml, 'trade_buy_button', make_button)
    xml = sub_block(xml, 'trade_sell_button', make_button)
    return xml


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(text.encode('utf-8'))


mod_src = read(A.mod_xml)
b43_src = read(A.base_xml43)
ui = os.path.join(out, 'gamedata', 'configs', 'ui')
write(os.path.join(ui, 'actor_menu.xml'), build_xml(mod_src, True, False))
write(os.path.join(ui, 'actor_menu_4x3.xml'), build_xml(b43_src, False, False))
opt = os.path.join(out, 'optional', 'soc_trade_top', 'gamedata', 'configs', 'ui')
write(os.path.join(opt, 'actor_menu.xml'), build_xml(mod_src, True, True))
write(os.path.join(opt, 'actor_menu_4x3.xml'), build_xml(b43_src, False, True))

if A.preview:
    os.makedirs(A.preview, exist_ok=True)
    over(wide, (60, 60, 60)).save(os.path.join(A.preview, 'wide.png'))
    over(n43, (60, 60, 60)).save(os.path.join(A.preview, 'n43.png'))
    over(ATL, (60, 60, 60)).save(os.path.join(A.preview, 'atlas.png'))
    for s in 'ehtd':
        over(button(s, 201, 37), (60, 60, 60)).save(os.path.join(A.preview, 'btn_%s.png' % s))
print('done', wide_s.size, n43_s.size, 'btn x', XB)
