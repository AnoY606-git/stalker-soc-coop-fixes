"""Regenerates every main menu style of the soc_main_menu patch.

Usage: python gen_styles.py <default style: ue4_a | ue4_b | soc>

- patches\\soc_main_menu\\gamedata\\configs\\ui\\ui_mm_main.xml + configs\\misc\\socfx_mm.ltx = the DEFAULT style (shipped in every build)
- optional\\mm_style_<name>\\gamedata\\... = the other styles (build.py --mm-style=<name> lays them over the default):
  the xml + ltx pair, and for soc also the SoC only art (sky and fire videos, side strips) that the UE4 styles do not need.
The mod's own ui_mm_main.xml is only read for the page / button list.
"""
import os
import shutil
import subprocess
import sys

repo = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
pd = os.path.join(repo, 'patches', 'soc_main_menu')
default = sys.argv[1]
assert default != 'soc', 'the SoC style needs its sky and fire videos shipped in the patch; move optional/mm_style_soc/gamedata/textures first'
modxml = os.path.expandvars(r'%USERPROFILE%\Downloads\Shadow of COOP 8.0\source\gamedata.db0\configs\ui\ui_mm_main.xml')
gen = os.path.join(pd, 'tools', 'gen_ui_mm_main.py')


def make(style, outdir):
    subprocess.check_call([sys.executable, '-I', gen, modxml, outdir, style])


make(default, os.path.join(pd, 'gamedata'))
for style in ('soc', 'ue4_a', 'ue4_b'):
    od = os.path.join(repo, 'optional', 'mm_style_' + style, 'gamedata')
    if style == default:
        shutil.rmtree(os.path.join(repo, 'optional', 'mm_style_' + style), ignore_errors=True)
        continue
    make(style, od)
print('default style', default)
