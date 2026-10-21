r"""Convert an original Shadow of Chernobyl hero mesh (meshes\actors\hero\*.ogf from the SoC install) so the xrMPE (Call of Pripyat)
renderer and animations accept it.  Used for stalker_marked_one.ogf (source: stalker_novice.ogf, the visual SoC itself gives the
Marked One in configs\gameplay\character_desc_general.xml) and for the worn-suit visuals (the other actors\hero\*.ogf).

Usage:  python -I soc_hero_to_xrmpe.py <soc.ogf> <xrmpe_donor.ogf> <out.ogf> [--tex-prefix mo_] [--keep act\act_bandit,act\act_soldier]
  donor = any xrMPE/CoP actor skeleton model, e.g. meshes\actors\stalker_hero\stalker_hero_1.ogf (read it from patches\xrmpe_meshes_actors.db0).
  --tex-prefix renames every texture "dir\name" inside the mesh to "dir\<prefix>name" (the SoC originals are then shipped under the new
  names, so Call of Pripyat textures of the same name are not overridden); --keep lists textures that stay as they are.

What differs between the two rigs (measured on the real files):
  * CoP puts two extra root bones (root_stalker, bip01) above bip01_pelvis, so every vertex bone id shifts by 2.
  * SoC's pelvis is the root and carries a 180 degree yaw plus the world height; CoP's pelvis has no yaw and sits under bip01.
    The pelvis bind pose is replaced and every vertex position/normal/tangent/binormal and the bounding boxes are turned 180 degrees
    about Y (x -> -x, z -> -z) so the mesh keeps facing the right way.
  * The motion reference list (animation packs) is taken from the donor (chunk 24) instead of SoC's single pack.
A raw SoC mesh crashes xrRender_R4 as soon as the lobby/spawn creates it; the converted file loads, animates and ragdolls.
"""
import struct
import sys

NUL = b'\x00'


def read_chunks(d):
    pos, out = 0, []
    while pos + 8 <= len(d):
        cid, sz = struct.unpack_from('<II', d, pos)
        out.append((cid & 0x7fffffff, d[pos + 8:pos + 8 + sz]))
        pos += 8 + sz
    return out


def write_chunks(chs):
    return b''.join(struct.pack('<II', cid, len(b)) + b for cid, b in chs)


def cstr(b, pos):
    e = b.index(NUL, pos)
    return b[pos:e].decode('cp1251'), e + 1


def parse_bone_names(body):
    """chunk 13: u32 count, per bone: name, parent, obb (15 floats)."""
    n = struct.unpack_from('<I', body, 0)[0]
    pos, bones = 4, []
    for _ in range(n):
        name, pos = cstr(body, pos)
        par, pos = cstr(body, pos)
        bones.append([name, par, body[pos:pos + 60]])
        pos += 60
    assert pos == len(body)
    return bones


def build_bone_names(bones):
    out = struct.pack('<I', len(bones))
    for name, par, obb in bones:
        out += name.encode('cp1251') + NUL + par.encode('cp1251') + NUL + obb
    return out


def parse_ikdata(body, nbones):
    """chunk 16: per bone u32 version, material, shape (112 bytes), joint (72 bytes, +4 friction when version >= 1),
    bind rotation (3f), bind offset (3f), mass (f), centre of mass (3f).  Returns the raw per-bone records."""
    pos, recs = 0, []
    for _ in range(nbones):
        start = pos
        ver = struct.unpack_from('<I', body, pos)[0]
        pos += 4
        _, pos = cstr(body, pos)
        pos += 112 + 72 + (4 if ver >= 1 else 0) + 40
        recs.append(body[start:pos])
    assert pos == len(body)
    return recs


def flip_header(sb):
    """OGF header: u8 version, u8 type, u16 shader, bbox min (3f), bbox max (3f), sphere centre (3f) + radius."""
    h = bytearray(sb)
    mn = struct.unpack_from('<3f', h, 4)
    mx = struct.unpack_from('<3f', h, 16)
    c = struct.unpack_from('<3f', h, 28)
    struct.pack_into('<3f', h, 4, -mx[0], mn[1], -mx[2])
    struct.pack_into('<3f', h, 16, -mn[0], mx[1], -mn[2])
    struct.pack_into('<3f', h, 28, -c[0], c[1], -c[2])
    return bytes(h)


def convert_children(body, shift, rename=None):
    out = bytearray()
    pos = 0
    while pos + 8 <= len(body):
        cid, sz = struct.unpack_from('<II', body, pos)
        newsubs = []
        for sid, sb in read_chunks(body[pos + 8:pos + 8 + sz]):
            if sid == 1:
                sb = flip_header(sb)
            elif sid == 2 and rename:   # texture NUL shader NUL
                parts = sb.split(NUL)
                parts[0] = rename(parts[0].decode('cp1251')).encode('cp1251')
                sb = NUL.join(parts)
            elif sid == 3:   # vertices
                fvf, cnt = struct.unpack_from('<II', sb, 0)
                data = bytearray(sb)
                if fvf == 0x12071980:    # 1 link: P N T B uv (56 bytes) + u32 bone id
                    vs, f_off = 60, (0, 12, 24, 36)
                elif fvf == 0x240e3300:  # 2 links: u16 id0, u16 id1, P N T B, f weight, uv
                    vs, f_off = 64, (4, 16, 28, 40)
                else:
                    raise SystemExit('unknown vertex format 0x%x' % fvf)
                assert len(sb) == 8 + vs * cnt
                for i in range(cnt):
                    o = 8 + i * vs
                    if fvf == 0x12071980:
                        (m,) = struct.unpack_from('<I', data, o + 56)
                        struct.pack_into('<I', data, o + 56, m + shift)
                    else:
                        a, b = struct.unpack_from('<HH', data, o)
                        struct.pack_into('<HH', data, o, a + shift, b + shift)
                    for fo in f_off:
                        x, y, z = struct.unpack_from('<3f', data, o + fo)
                        struct.pack_into('<3f', data, o + fo, -x, y, -z)
                sb = bytes(data)
            newsubs.append((sid, sb))
        nb = write_chunks(newsubs)
        out += struct.pack('<II', cid, len(nb)) + nb
        pos += 8 + sz
    return bytes(out)


def textures_of(path):
    """Texture names used by a mesh (list of (texture, shader))."""
    res = set()
    for cid, body in read_chunks(open(path, 'rb').read()):
        if cid == 9:
            pos = 0
            while pos + 8 <= len(body):
                _, sz = struct.unpack_from('<II', body, pos)
                for sid, sb in read_chunks(body[pos + 8:pos + 8 + sz]):
                    if sid == 2:
                        t = sb.split(NUL)
                        res.add((t[0].decode('cp1251'), t[1].decode('cp1251')))
                pos += 8 + sz
    return sorted(res)


def main(soc_path, donor_path, out_path, rename=None):
    soc = read_chunks(open(soc_path, 'rb').read())
    socd = dict(soc)
    cop = dict(read_chunks(open(donor_path, 'rb').read()))
    bones_soc = parse_bone_names(socd[13])
    bones_cop = parse_bone_names(cop[13])
    assert [b[0] for b in bones_cop[:2]] == ['root_stalker', 'bip01']
    assert [b[0] for b in bones_cop[2:]] == [b[0] for b in bones_soc], 'bone lists differ after the two roots'
    shift = 2

    new_bones = [list(bones_cop[0]), list(bones_cop[1])] + [list(b) for b in bones_soc]
    assert new_bones[2][0] == 'bip01_pelvis' and new_bones[2][1] == ''
    new_bones[2][1] = 'bip01'

    ik_soc = parse_ikdata(socd[16], len(bones_soc))
    ik_cop = parse_ikdata(cop[16], len(bones_cop))
    rot_cop = ik_cop[2][-40:-28]
    pos_soc = struct.unpack_from('<3f', ik_soc[0], len(ik_soc[0]) - 28)
    pos_bip = struct.unpack_from('<3f', ik_cop[1], len(ik_cop[1]) - 28)
    newpos = struct.pack('<3f', *[pos_soc[i] - pos_bip[i] for i in range(3)])
    pelvis = ik_soc[0][:-40] + rot_cop + newpos + ik_soc[0][-16:]
    c16 = ik_cop[0] + ik_cop[1] + pelvis + b''.join(ik_soc[1:])

    out = []
    for cid, body in soc:
        if cid == 1:
            out.append((1, flip_header(body)))
        elif cid == 9:
            out.append((9, convert_children(body, shift, rename)))
        elif cid == 13:
            out.append((13, build_bone_names(new_bones)))
        elif cid == 16:
            out.append((16, c16))
        elif cid == 19:    # SoC single motion pack -> the donor's pack list (chunk 24)
            out.append((24, cop[24]))
        else:
            out.append((cid, body))
    data = write_chunks(out)
    open(out_path, 'wb').write(data)
    print('written', out_path, len(data), 'bytes')


def make_rename(prefix, keep):
    keep = set(k.lower() for k in keep)

    def rename(tex):
        if tex.lower() in keep:
            return tex
        d, _, n = tex.rpartition(chr(92))
        return (d + chr(92) if d else '') + prefix + n
    return rename


if __name__ == '__main__':
    a = sys.argv[1:]
    prefix, keep = None, []
    if '--tex-prefix' in a:
        i = a.index('--tex-prefix')
        prefix = a[i + 1]
        del a[i:i + 2]
    if '--keep' in a:
        i = a.index('--keep')
        keep = a[i + 1].split(',')
        del a[i:i + 2]
    main(a[0], a[1], a[2], make_rename(prefix, keep) if prefix else None)
