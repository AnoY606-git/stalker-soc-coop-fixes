"""Builds gamedata/textures/ui/ui_rq_task_icons.dds and configs/ui/textures_descr/ui_rq_task_icons.xml for the repeatable quests.
Source: the SoC icon atlas ui_iconsTotal (1024x1024 DDS, the SoC regions of its textures_descr), 83x47 cells copied into a small A8R8G8B8 atlas.
python make_icons.py <ui_iconstotal.dds> <patch dir (repeatable_quests)>"""
import sys, os, struct
from PIL import Image
src, patch = sys.argv[1], sys.argv[2]
CELLS = [  # new id, SoC id, x, y in ui_iconsTotal
	("ui_rq_job_trader",    "ui_iconsTotal_esc_trader_job",         249, 611),
	("ui_rq_job_barman",    "ui_iconsTotal_bar_barman_job",         249, 658),
	("ui_rq_job_scientist", "ui_iconsTotal_yan_scientist_job",      249, 705),
	("ui_rq_task_kill",     "ui_iconsTotal_kill_stalker",           0, 235),
	("ui_rq_task_camp",     "ui_iconsTotal_eliminate_lager",        0, 376),
	("ui_rq_task_defend",   "ui_iconsTotal_defend_lager",           249, 564),
	("ui_rq_task_find",     "ui_iconsTotal_find_item",              0, 188),
]
W, H, CW, CH, COLS = 256, 256, 83, 47, 3
atlas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sheet = Image.open(src).convert("RGBA")
xml = ['<w>', '\t<file name="ui\\ui_rq_task_icons">']
for n, (nid, soc, sx, sy) in enumerate(CELLS):
	dx, dy = (n % COLS) * CW, (n // COLS) * CH
	atlas.paste(sheet.crop((sx, sy, sx + CW, sy + CH)), (dx, dy))
	xml.append('\t\t<texture id="%s" x="%d" y="%d" width="%d" height="%d" />' % (nid, dx, dy, CW, CH))
xml += ['\t</file>', '</w>']
hdr = b"DDS " + struct.pack("<7I", 124, 0x100F, H, W, W * 4, 0, 0) + b"\0" * 44
hdr += struct.pack("<8I", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000) + struct.pack("<5I", 0x1000, 0, 0, 0, 0)
assert len(hdr) == 128
px = bytearray()
raw = atlas.tobytes()
for i in range(0, len(raw), 4):
	px += bytes((raw[i + 2], raw[i + 1], raw[i], raw[i + 3]))
out = os.path.join(patch, "gamedata", "textures", "ui", "ui_rq_task_icons.dds")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "wb").write(hdr + bytes(px))
xo = os.path.join(patch, "gamedata", "configs", "ui", "textures_descr", "ui_rq_task_icons.xml")
os.makedirs(os.path.dirname(xo), exist_ok=True)
open(xo, "wb").write(("\r\n".join(xml) + "\r\n").encode("ascii"))
print("wrote", out, os.path.getsize(out), "and", xo)
