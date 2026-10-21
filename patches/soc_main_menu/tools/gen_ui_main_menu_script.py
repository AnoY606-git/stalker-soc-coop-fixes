"""Builds scripts\\ui_main_menu.script = the mod's own script + tools\\hooks_append.lua (the SoC selector hooks).

Usage: python gen_ui_main_menu_script.py <mod ui_main_menu.script> <out ui_main_menu.script>
"""
import os
import sys

src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
base = open(src, 'rb').read().decode('utf-8').replace('\r\n', '\n').rstrip('\n')
hooks = open(os.path.join(here, 'hooks_append.lua'), encoding='utf-8').read().replace('\r\n', '\n').rstrip('\n')
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
open(dst, 'wb').write((base + '\n' + hooks + '\n').replace('\n', '\r\n').encode('utf-8'))
print('wrote', dst)
