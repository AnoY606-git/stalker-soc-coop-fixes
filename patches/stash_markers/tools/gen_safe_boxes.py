#!/usr/bin/env python3
"""Builds the safe-zone storage box data of patches/stash_markers:
  gamedata/scripts/safe_box_data.script                 (box names, positions, hint keys)
  gamedata/configs/text/rus/safe_box_markers.xml        (windows-1251)
  gamedata/configs/text/eng/safe_box_markers.xml

Safe zones (one entry per base). A box counts when it is an `inventory_box` of the add-on level.spawn that stands inside
the zone and carries NO preset loot (a [spawn] section with items is a loot cache: those belong to the stash markers).
  * Cordon Sidorovich's bunker, Bar (both), Yantar (both): the no-weapon space restrictors the mod uses (their box shape)
  * Cordon rookie village, the Garbage Duty checkpoint and the Army Warehouses Freedom base: no no-weapon restrictor exists, so a circle (x, z) around the camp

  python gen_safe_boxes.py [--addon <addon_unpacked>] [--list]
"""
import argparse, math, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import xdb  # noqa: E402

# key, level, kind, argument, Russian place, English place
ZONES = [
    ('esc_bunker', 'coop_l01_escape', 'restrictor', ['esc_sr_no_weapon_space_restrictor'],
     'Бункер Сидоровича', "Sidorovich's bunker"),
    ('esc_village', 'coop_l01_escape', 'circle', (-206.9, -140.1, 30.0),
     'Лагерь новичков', 'Rookie village'),
    ('gar_duty', 'coop_l02_garbage', 'circle', (40.0, 238.0, 20.0),
     'Блокпост Долга', 'Duty checkpoint'),
    ('bar_100rads', 'coop_l05_bar', 'restrictor', ['bar_sr_no_weapon_space_restrictor'],
     'Бар 100 рентген', 'The 100 Rads bar'),
    ('bar_duty', 'coop_l05_bar', 'restrictor', ['bar_sr_no_weapon_space_restrictor_0001'],
     'Территория Долга', 'Duty base'),
    ('yan_sakharov', 'coop_l08_yantar', 'restrictor',
     ['yan_sr_no_weapon_space_restrictor', 'yan_sr_no_weapon_space_restrictor_0000'],
     'Бункер Сахарова', "Sakharov's bunker"),
    ('mil_freedom', 'coop_l07_military', 'circle', (-30.0, -2.0, 55.0),
     'База Свободы', 'Freedom base'),
]
TITLE_RU, TITLE_EN = 'Ящик для вещей', 'Storage box'
COLOR = '%c[255,238,155,23]'


def read_level_spawns(addon):
    for dbn in ('gamedata.db0', 'gamedata.db1'):
        p = os.path.join(addon, dbn)
        f = open(p, 'rb')
        for name, rs, cs, ptr in xdb.index(f, 0, os.path.getsize(p)):
            m = re.match(r'levels\\(coop_[^\\]+)\\level\.spawn$', name)
            if not m:
                continue
            f.seek(ptr)
            d = f.read(cs)
            if rs != cs:
                d = xdb.lzo1x(d, rs)
            yield m.group(1), d


def objects(addon):
    for lv, d in read_level_spawns(addon):
        o = 0
        while o + 8 <= len(d):
            _, s = struct.unpack_from('<II', d, o)
            o += 8
            c = d[o:o + s]
            o += s
            mm = re.match(rb'\x01\x00([^\x00]*)\x00([^\x00]*)\x00', c)
            if not mm:
                continue
            sec, nm = mm.group(1).decode('latin1'), mm.group(2).decode('latin1')
            x, y, z = struct.unpack_from('<fff', c, mm.end() + 2)
            yield lv, sec, nm, (x, y, z), c, mm.end()


def box_shape(c, start):
    """First shape of a space restrictor: ('box', 12 floats) or ('sphere', cx, cy, cz, r)."""
    m = re.search(rb'\x00\xff\xff\xff\xff\xff\xff\xff\xff([\x01-\x08])', c[start + 40:])
    o = start + 40 + m.end() - 1
    o += 1  # shape count
    if c[o] == 0:
        return ('sphere',) + struct.unpack_from('<ffff', c, o + 1)
    return ('box', struct.unpack_from('<12f', c, o + 1))


def in_restrictor(p, rpos, shape):
    if shape[0] == 'sphere':
        _, cx, cy, cz, r = shape
        return math.dist((p[0], p[1], p[2]), (rpos[0] + cx, rpos[1] + cy, rpos[2] + cz)) <= r
    f = shape[1]  # axis aligned (the angles of these restrictors are 0); the matrix scale is the full size
    cx, cy, cz = rpos[0] + f[9], rpos[1] + f[10], rpos[2] + f[11]
    return abs(p[0] - cx) <= f[0] / 2 and abs(p[1] - cy) <= f[4] / 2 and abs(p[2] - cz) <= f[8] / 2


def custom_data(c, start):
    cd = re.search(rb'(\[[A-Za-z_0-9.]+\][\x09\x0a\x0d\x20-\x7e]*)', c[start:])
    return cd.group(1).decode('latin1') if cd else ''


def has_loot(cd):
    if '[spawn]' not in cd:
        return False
    body = cd.split('[spawn]', 1)[1]
    body = re.split(r'\r?\n\[', body)[0]
    return any(l.strip() for l in body.split('\n'))


def collect(addon):
    objs = list(objects(addon))
    rest = {}
    for lv, sec, nm, pos, c, st in objs:
        if sec == 'space_restrictor':
            rest[(lv, nm)] = (pos, box_shape(c, st) if b'no_weapon' in c else None)
    found, skipped = [], []
    for lv, sec, nm, pos, c, st in objs:
        if sec != 'inventory_box':
            continue
        cd = custom_data(c, st)
        for key, zlv, kind, arg, _, _ in ZONES:
            if zlv != lv:
                continue
            if kind == 'restrictor':
                inside = any(in_restrictor(pos, rest[(lv, r)][0], rest[(lv, r)][1]) for r in arg)
            else:
                inside = math.hypot(pos[0] - arg[0], pos[2] - arg[1]) <= arg[2]
            if not inside:
                continue
            (skipped if has_loot(cd) else found).append((key, lv, nm, pos))
            break
    order = {z[0]: i for i, z in enumerate(ZONES)}
    found.sort(key=lambda b: (order[b[0]], b[2]))
    skipped.sort(key=lambda b: (order[b[0]], b[2]))
    return found, skipped


def write_all(found):
    sc = os.path.join(HERE, '..', 'gamedata', 'scripts', 'safe_box_data.script')
    L = ['-- GENERATED by tools/gen_safe_boxes.py, do not edit. Storage boxes (inventory_box without preset loot) inside the safe zones.',
         '-- name = object name (same in level.spawn and all.spawn), lvl = level, key = hint string safe_box_hint_<key>, x/y/z = level position.',
         'spot = "safe_box_location"', '', 'boxes = {']
    for key, lv, nm, p in found:
        L.append('\t{name="%s",lvl="%s",key="%s",x=%.1f,y=%.1f,z=%.1f},' % (nm, lv, key, p[0], p[1], p[2]))
    L.append('}')
    open(sc, 'wb').write(('\r\n'.join(L) + '\r\n').encode('ascii'))
    for lang, enc in (('rus', 'cp1251'), ('eng', 'cp1251')):
        ru = lang == 'rus'
        S = ['<?xml version="1.0" encoding="windows-1251" ?>', '<string_table>',
             '\t<string id="safe_box_hint">', '\t\t<text>%s</text>' % (TITLE_RU if ru else TITLE_EN), '\t</string>']
        used = sorted({b[0] for b in found}, key=lambda k: [z[0] for z in ZONES].index(k))
        for z in ZONES:
            if z[0] in used:
                S += ['\t<string id="safe_box_hint_%s">' % z[0],
                      '\t\t<text>%s%s\\n%%c[default]%s.</text>' % (COLOR, TITLE_RU if ru else TITLE_EN, z[4] if ru else z[5]),
                      '\t</string>']
        S.append('</string_table>')
        p = os.path.join(HERE, '..', 'gamedata', 'configs', 'text', lang, 'safe_box_markers.xml')
        open(p, 'wb').write(('\r\n'.join(S) + '\r\n').encode(enc))


def main():
    ap = argparse.ArgumentParser()
    dl = os.path.join(os.path.expanduser('~'), 'Downloads')
    ap.add_argument('--addon', default=os.path.join(dl, 'Shadow of COOP 8.0', 'addon_unpacked'))
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    found, skipped = collect(a.addon)
    sys.stdout.reconfigure(encoding='utf-8')
    for tag, lst in (('BOX', found), ('SKIPPED (preset loot)', skipped)):
        for key, lv, nm, p in lst:
            print('%-22s %-10s %-18s %-36s %.1f, %.1f, %.1f' % (tag, key, lv, nm, p[0], p[1], p[2]))
    if not a.list:
        write_all(found)
        print('wrote', len(found), 'boxes')


if __name__ == '__main__':
    main()
