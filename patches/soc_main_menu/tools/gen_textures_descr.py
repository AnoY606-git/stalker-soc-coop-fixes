"""Builds gamedata\\configs\\ui\\textures_descr\\socfx_mm.xml from the original SoC ui_mainmenu.xml.

Usage: python gen_textures_descr.py <SoC ui_mainmenu.xml> <out socfx_mm.xml>
The original ids ui_menu_* are renamed socfx_mm_* so they cannot collide with anything in CoP / xrMPE / the mod.
The sheet itself is the original SoC textures\\ui\\ui_mainmenu.dds, shipped as textures\\ui\\socfx_mm_sheet.dds.
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8', errors='replace').read()
rows = []
for m in re.finditer(r'<texture id="(\w+)" x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"', text):
    name, x, y, w, h = m.groups()
    new = re.sub(r'^ui_menu_', 'socfx_mm_', name)
    new = new.replace('backgraund', 'bg')
    rows.append('\t\t<texture id="%s" x="%s" y="%s" width="%s" height="%s" />' % (new, x, y, w, h))
out = ['<w>', '\t<file name="ui\\socfx_mm_sheet">']
out += rows
out += ['\t</file>', '\t<file name="ui\\socfx_mm_clear">']
for st in 'etdh':
    out.append('\t\t<texture id="socfx_mm_btn_%s" x="0" y="0" width="8" height="8" />' % st)
out += ['\t</file>', '\t<file name="ui\\socfx_mm_left">',
        '\t\t<texture id="socfx_mm_left" x="0" y="0" width="400" height="768" />',
        '\t\t<texture id="socfx_mm_black" x="0" y="0" width="4" height="4" />', '\t</file>',
        '\t<file name="ui\\socfx_ue4_panel">',
        '\t\t<texture id="socfx_ue4_panel" x="0" y="0" width="217" height="360" />', '\t</file>',
        '\t<file name="ui\\socfx_mm_right">',
        '\t\t<texture id="socfx_mm_right" x="0" y="0" width="400" height="768" />', '\t</file>', '</w>', '']
open(dst, 'w', encoding='utf-8', newline='\r\n').write('\n'.join(out))
print(len(rows), 'textures ->', dst)
