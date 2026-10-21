"""Length of ogg vorbis files in milliseconds, plus a 300 ms margin (the value the opening script uses for its `ms`).

usage: python ogg_ms.py <file or folder> [...]
Reads the sample rate from the identification header and the granule position of the last page. No third-party modules.
"""
import os, struct, sys


def ogg_seconds(path):
    d = open(path, "rb").read()
    if d[:4] != b"OggS":
        raise ValueError("not an ogg file: " + path)
    # identification header is the first packet: 0x01 'vorbis', version u32, channels u8, rate u32
    i = d.find(b"\x01vorbis")
    rate = struct.unpack_from("<I", d, i + 12)[0]
    # granule position of the last page
    j = d.rfind(b"OggS")
    gp = struct.unpack_from("<q", d, j + 6)[0]
    return gp / float(rate)


def main(args):
    for a in args:
        files = []
        if os.path.isdir(a):
            for r, _, fs in os.walk(a):
                files += [os.path.join(r, f) for f in fs if f.lower().endswith(".ogg")]
        else:
            files.append(a)
        for f in sorted(files):
            s = ogg_seconds(f)
            print("%-60s %8.3f s  ms=%d" % (os.path.relpath(f), s, int(round(s * 1000)) + 300))


if __name__ == "__main__":
    main(sys.argv[1:] or ["."])
