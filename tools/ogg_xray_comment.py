"""Read / write the X-Ray engine sound parameters stored in the first vorbis user comment of an .ogg.

The engine (xrSound, CSoundRender_Source::load) reads vorbis_comment.user_comments[0] as a binary block:
  u32 version
  v1 (0x0001): f32 min_dist, f32 max_dist, u32 game_type                      (base volume 1.0)
  v2 (0x0002): f32 min_dist, f32 max_dist, f32 base_volume, u32 game_type
  v3 (0x0003): f32 min_dist, f32 max_dist, f32 base_volume, u32 game_type, f32 max_ai_dist
No comment at all: the engine logs "! Missing ogg-comment" and uses min 1, max 300, volume 1, ai dist 300.

  python -I ogg_xray_comment.py show <file.ogg|dir> ...
  python -I ogg_xray_comment.py set <file.ogg> <out.ogg> --min M --max X [--volume V] [--ai A] [--type T]
"""
import os
import struct
import sys

_CRC = []
for _i in range(256):
    _r = _i << 24
    for _ in range(8):
        _r = ((_r << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if _r & 0x80000000 else (_r << 1) & 0xFFFFFFFF
    _CRC.append(_r)


def ogg_crc(data):
    c = 0
    for b in data:
        c = ((c << 8) & 0xFFFFFFFF) ^ _CRC[((c >> 24) ^ b) & 0xFF]
    return c


def read_pages(data):
    """-> list of dicts: header fields + list of (segment bytes lengths) + body"""
    pages = []
    pos = 0
    while pos < len(data):
        if data[pos:pos + 4] != b'OggS':
            raise ValueError('bad page at %d' % pos)
        htype = data[pos + 5]
        granule = data[pos + 6:pos + 14]
        serial, seq = struct.unpack_from('<II', data, pos + 14)
        nseg = data[pos + 26]
        lacing = list(data[pos + 27:pos + 27 + nseg])
        body_len = sum(lacing)
        body = data[pos + 27 + nseg:pos + 27 + nseg + body_len]
        pages.append(dict(htype=htype, granule=granule, serial=serial, seq=seq, lacing=lacing, body=body))
        pos += 27 + nseg + body_len
    return pages


def packets_of_first_pages(pages, want=3):
    """Collect the first `want` packets (spanning pages). Returns (packets, index of first page that is
    not fully consumed, bytes of that page's body left over, lacing left over)."""
    packets = []
    cur = b''
    for pi, pg in enumerate(pages):
        off = 0
        for si, seg in enumerate(pg['lacing']):
            cur += pg['body'][off:off + seg]
            off += seg
            if seg < 255:
                packets.append(cur)
                cur = b''
                if len(packets) == want:
                    rest_body = pg['body'][off:]
                    rest_lacing = pg['lacing'][si + 1:]
                    return packets, pi, rest_body, rest_lacing
    raise ValueError('not enough packets')


def parse_comment_packet(pkt):
    """pkt = vorbis comment header packet. -> (vendor bytes, [comment bytes], framing)"""
    if pkt[:7] != b'\x03vorbis':
        raise ValueError('not a vorbis comment packet')
    p = 7
    vl, = struct.unpack_from('<I', pkt, p)
    p += 4
    vendor = pkt[p:p + vl]
    p += vl
    n, = struct.unpack_from('<I', pkt, p)
    p += 4
    comments = []
    for _ in range(n):
        cl, = struct.unpack_from('<I', pkt, p)
        p += 4
        comments.append(pkt[p:p + cl])
        p += cl
    return vendor, comments, pkt[p:]


def decode_block(b):
    """-> dict with version/min/max/volume/game_type/ai (volume None for v1, ai None for v1/v2) or None if not X-Ray"""
    if len(b) < 4:
        return None
    ver, = struct.unpack_from('<I', b, 0)
    if ver == 1 and len(b) >= 16:
        mn, mx, gt = struct.unpack_from('<ffI', b, 4)
        return dict(version=1, min=mn, max=mx, volume=1.0, game_type=gt, ai=mx, raw_len=len(b))
    if ver == 2 and len(b) >= 20:
        mn, mx, vol, gt = struct.unpack_from('<fffI', b, 4)
        return dict(version=2, min=mn, max=mx, volume=vol, game_type=gt, ai=mx, raw_len=len(b))
    if ver == 3 and len(b) >= 24:
        mn, mx, vol, gt, ai = struct.unpack_from('<fffIf', b, 4)
        return dict(version=3, min=mn, max=mx, volume=vol, game_type=gt, ai=ai, raw_len=len(b))
    return None


def encode_block(mn, mx, vol, gt, ai):
    return struct.pack('<IfffIf', 3, mn, mx, vol, gt, ai)


def describe(path):
    data = open(path, 'rb').read()
    pages = read_pages(data)
    pk, _, _, _ = packets_of_first_pages(pages)
    vendor, comments, _ = parse_comment_packet(pk[1])
    if not comments:
        return None, 'MISSING (engine defaults: min 1, max 300, vol 1, ai 300)'
    d = decode_block(comments[0])
    if d is None:
        return None, 'unreadable first comment %r' % comments[0][:24]
    return d, 'v%d min %.1f max %.1f vol %.2f type %d ai %.1f (%d comments)' % (
        d['version'], d['min'], d['max'], d['volume'], d['game_type'], d['ai'], len(comments))


def rewrite(path_in, path_out, mn, mx, vol, gt, ai):
    """Replace comment 0 (insert one when missing) and re-page the stream: header pages are rebuilt, audio pages
    are copied untouched except for the sequence number if the header page count changed."""
    data = open(path_in, 'rb').read()
    pages = read_pages(data)
    pk, pi, rest_body, rest_lacing = packets_of_first_pages(pages)
    vendor, comments, framing = parse_comment_packet(pk[1])
    blk = encode_block(mn, mx, vol, gt, ai)
    comments = [blk] + comments[1:] if comments else [blk]
    cp = b'\x03vorbis' + struct.pack('<I', len(vendor)) + vendor + struct.pack('<I', len(comments))
    for c in comments:
        cp += struct.pack('<I', len(c)) + c
    cp += framing if framing else b'\x01'
    serial = pages[0]['serial']
    out = bytearray()
    seq = 0

    def emit(htype, granule, lacing, body):
        nonlocal seq
        hdr = bytearray(b'OggS\x00')
        hdr.append(htype)
        hdr += granule
        hdr += struct.pack('<III', serial, seq, 0)
        hdr.append(len(lacing))
        hdr += bytes(lacing)
        page = bytes(hdr) + body
        crc = ogg_crc(page)
        page = page[:22] + struct.pack('<I', crc) + page[26:]
        out.extend(page)
        seq += 1

    def lace(pkt):
        l = []
        n = len(pkt)
        while n >= 255:
            l.append(255)
            n -= 255
        l.append(n)
        return l

    # page 0: identification packet alone (bos). page 1: comment + setup (+ whatever follows on the old page)
    emit(pages[0]['htype'], pages[0]['granule'], lace(pk[0]), pk[0])
    lacing = lace(cp) + lace(pk[2])
    body = cp + pk[2]
    if len(lacing) > 255:
        raise ValueError('header too large for one page')
    if rest_lacing:
        raise ValueError('audio data shares the header page, not supported')
    if len(lacing) > 255:
        raise ValueError('header page overflow')
    emit(0, b'\x00' * 8, lacing, body)
    for pg in pages[pi + 1:]:
        emit(pg['htype'], pg['granule'], pg['lacing'], pg['body'])
    open(path_out, 'wb').write(bytes(out))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[0] == 'show':
        for a in argv[1:]:
            paths = []
            if os.path.isdir(a):
                for r, _, fs in os.walk(a):
                    paths += [os.path.join(r, f) for f in sorted(fs) if f.lower().endswith('.ogg')]
            else:
                paths = [a]
            for p in paths:
                print(os.path.basename(p), '|', describe(p)[1])
        return 0
    if argv[0] == 'set':
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument('cmd')
        ap.add_argument('src')
        ap.add_argument('dst')
        ap.add_argument('--min', type=float, required=True)
        ap.add_argument('--max', type=float, required=True)
        ap.add_argument('--volume', type=float, default=None)
        ap.add_argument('--ai', type=float, default=None)
        ap.add_argument('--type', type=int, default=None)
        a = ap.parse_args(argv)
        old, _ = describe(a.src)
        vol = a.volume if a.volume is not None else (old['volume'] if old else 1.0)
        gt = a.type if a.type is not None else (old['game_type'] if old else 0)
        ai = a.ai if a.ai is not None else (old['ai'] if old else a.max)
        rewrite(a.src, a.dst, a.min, a.max, vol, gt, ai)
        print(a.dst, '|', describe(a.dst)[1])
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
