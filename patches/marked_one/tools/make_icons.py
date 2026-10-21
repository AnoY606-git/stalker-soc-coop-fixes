"""Builds textures/ui/ui_marked_one_icons.dds from the SoC icon atlas ui_iconstotal.dds.

The Marked One portrait is the region `ui_npc_u_actor` of the atlas (x=694 y=216 165x108).
Usage: python make_icons.py <ui_iconstotal.dds> <out ui_marked_one_icons.dds> [<preview dir>]

Layout of the output (512x256, uncompressed 32 bit like the file it replaces, no mipmaps):
  stalker_marked_one            (  0,  0) 120x120  lobby character list (square crop around the face, opaque)
  ui_actor_p_stalker_marked_one (  0,128) 165x108  the original SoC portrait, unchanged
  ui_marked_one_hero            (256,  0) 153x108  inventory / PDA / dialog portrait (same ratio as the
                                                    123x87 ui_inGame2_Hero it replaces, centre crop, opaque)
"""
import struct
import sys
import os
from PIL import Image

SRC = (694, 216, 165, 108)
FACE_CX = 88  # face centre inside the 165 px wide source (measured on the reference)


def main():
    atlas = Image.open(sys.argv[1]).convert("RGBA")
    out = sys.argv[2]
    prev = sys.argv[3] if len(sys.argv) > 3 else None
    x, y, w, h = SRC
    full = atlas.crop((x, y, x + w, y + h))  # 165x108
    # the source has a torn (transparent) top edge and ragged side edges: the two crops below start at row 6
    # and stay inside columns 5..160, so they are fully opaque
    hero = full.crop((10, 6, 10 + 145, 108)).resize((153, 108), Image.LANCZOS)
    x0 = FACE_CX - 51
    sq = full.crop((x0, 6, x0 + 102, 108)).resize((120, 120), Image.LANCZOS)

    sheet = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    sheet.paste(sq, (0, 0))
    sheet.paste(full, (0, 128))
    sheet.paste(hero, (256, 0))

    # 32 bit BGRA, same header fields as the previous file (flags 0x100f, pitch, masks, no mipmaps)
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<7I", hdr, 4, 124, 0x100F, 256, 512, 512 * 4, 0, 0)
    struct.pack_into("<I", hdr, 76, 32)
    struct.pack_into("<I", hdr, 80, 0x41)
    struct.pack_into("<I", hdr, 88, 32)
    struct.pack_into("<4I", hdr, 92, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    struct.pack_into("<I", hdr, 108, 0x1000)
    r, g, b, a = sheet.split()
    data = Image.merge("RGBA", (b, g, r, a)).tobytes()
    with open(out, "wb") as f:
        f.write(bytes(hdr) + data)
    if prev:
        os.makedirs(prev, exist_ok=True)
        sheet.save(os.path.join(prev, "ui_marked_one_icons_NEW.png"))
        sq.resize((360, 360), Image.LANCZOS).save(os.path.join(prev, "lobby_icon_NEW_x3.png"))
        hero.resize((459, 324), Image.LANCZOS).save(os.path.join(prev, "inventory_icon_NEW_x3.png"))


main()
