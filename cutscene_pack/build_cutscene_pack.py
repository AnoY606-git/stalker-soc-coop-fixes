# Builds the "cutscene pack" of Shadow of COOP: the original S.T.A.L.K.E.R. SoC movies and movie sound tracks that the Scene Director
# (patches\cutscenes_core + cutscenes_pkg_*) plays. They do NOT go into coop.addon (4 GiB limit), they are separate X-Ray archives that
# a player copies to <xrMPE>\game\patches\ (see install_cutscenes.ps1 and README_cutscenes.txt).
#
#   python build_cutscene_pack.py extract --ru-sounds DIR [--steam-script PATH]
#       English: from the Steam SoC archives (tools\xdb_soc.py) into media\eng_raw.
#       Russian: DIR = folder that holds characters_voice\scenario\video\*.ogg (the original Russian sounds); copied to media\rus_raw.
#   python build_cutscene_pack.py build [--addon PATH\coop.addon]
#       Stages media\ into three archives in out\ and verifies them (tools\verify_db.py round trip). With --addon the probe check
#       (every `need` of the scene packages, every <sound> of the movie tutorial blocks) also counts the files the mod already ships.
#
# Archives (all stored raw, no compression: ogm/ogg are already compressed, and the installer's -Loose mode reads them back):
#   zz_soc_cutscenes.db              the 4 movies (language free)
#   zz_soc_cutscenes_voice_rus.db    movie sound tracks, original Russian
#   zz_soc_cutscenes_voice_eng.db    movie sound tracks, English (Steam SoC)
# The sound tracks are shipped three times each: <name>_l.ogg + <name>_r.ogg (the SoC pair, what the scene `need` probes test) and
# <name>.ogg (a copy of the left track: the xrMPE/CoP engine plays a tutorial <sound> as ONE file, like the mod's own final_*.ogg).
import os, re, shutil, struct, subprocess, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, 'tools')
MEDIA = os.path.join(HERE, 'media')
STAGE = os.path.join(HERE, 'stage')
OUT = os.path.join(HERE, 'out')
BS = chr(92)

MOVIES = ['dream_rats', 'dream_sarcofag', 'dream_doctor', 'dream_doctor_2']           # textures\intro\<name>.ogm
TRACKS = ['intro_stalker'] + MOVIES                                                    # sounds\characters_voice\scenario\video\<name>_l/_r.ogg
VIDEO_DIR = 'sounds' + BS + 'characters_voice' + BS + 'scenario' + BS + 'video'
SINGLES = [('sounds' + BS + 'characters_voice' + BS + 'scenario' + BS + 'osoznanie' + BS + 'teleport_osoznanie.ogg')]   # scene monolith_off

DBS = {
    'zz_soc_cutscenes.db': 'movies',
    'zz_soc_cutscenes_voice_rus.db': 'voice_rus',
    'zz_soc_cutscenes_voice_eng.db': 'voice_eng',
}
# Full HD movies (SoC Enhanced Edition Cutscenes by neatodev, https://www.nexusmods.com/stalkershadowofchernobyl/mods/1098): video only, under
# their own path textures\intro_hd\<name>.ogm (coop_scenes.hd_tutorial picks them when present). Optional archive, built when media\hd exists:
#   python build_cutscene_pack.py extract-hd <folder with textures\intro\*.ogm of that mod>
HD_MOVIES = ['intro_stalker', 'dream_rats', 'dream_sarcofag', 'dream_doctor', 'dream_doctor_2', 'final_blind', 'final_gold', 'final_to_monolith',
             'final_apocal', 'final_immortal', 'final_peace']
HD_DB = 'zz_soc_cutscenes_hd.db'
if os.path.isdir(os.path.join(MEDIA, 'hd')):
    DBS[HD_DB] = 'hd'


def die(msg):
    sys.exit('build_cutscene_pack: ' + msg)


def cmd_extract(args):
    ru = None
    steam_script = os.path.join(TOOLS, 'xdb_soc.py')
    i = 0
    while i < len(args):
        if args[i] == '--ru-sounds':
            ru = args[i + 1]; i += 1
        elif args[i] == '--steam-script':
            steam_script = args[i + 1]; i += 1
        else:
            die('unknown option ' + args[i])
        i += 1
    if not ru:
        die('extract needs --ru-sounds DIR')
    ru_video = None
    for base in (ru, os.path.join(ru, 'sounds')):
        if os.path.isdir(os.path.join(base, 'characters_voice', 'scenario', 'video')):
            ru_video = base
    if ru_video is None:
        die('no characters_voice\\scenario\\video under ' + ru)
    eng = os.path.join(MEDIA, 'eng_raw')
    rus = os.path.join(MEDIA, 'rus_raw')
    os.makedirs(eng, exist_ok=True)
    movies = '|'.join(MOVIES)
    tracks = '|'.join(TRACKS)
    pat = ('^textures.intro.(%s)\\.ogm$|^sounds.characters_voice.scenario.video.(%s)_[lr]\\.ogg$'
           '|^sounds.characters_voice.scenario.osoznanie.teleport_osoznanie\\.ogg$') % (movies, tracks)
    # xdb_soc.py caches its archive indexes (idx_*.pkl) in the current directory: run it from a scratch folder
    work = os.path.join(MEDIA, '_work')
    os.makedirs(work, exist_ok=True)
    subprocess.check_call([sys.executable, '-I', steam_script, pat, 'x', eng], cwd=work)
    shutil.rmtree(work, ignore_errors=True)
    n = 0
    for name in TRACKS:
        for ch in ('l', 'r'):
            src = os.path.join(ru_video, 'characters_voice', 'scenario', 'video', '%s_%s.ogg' % (name, ch))
            if not os.path.isfile(src):
                die('missing Russian track ' + src)
            dst = os.path.join(rus, VIDEO_DIR, '%s_%s.ogg' % (name, ch))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst); n += 1
    for rel in SINGLES:
        src = os.path.join(ru_video, rel.split(BS, 1)[1].replace(BS, os.sep))
        if not os.path.isfile(src):
            die('missing Russian file ' + src)
        dst = os.path.join(rus, rel.replace(BS, os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst); n += 1
    print('extract done: English in', eng, '; Russian', n, 'files in', rus)


def cmd_extract_hd(args):
    if not args:
        die('extract-hd needs the folder that holds textures\intro\*.ogm (or the intro folder itself)')
    src = args[0]
    for base in (src, os.path.join(src, 'textures', 'intro'), os.path.join(src, 'gamedata', 'textures', 'intro')):
        if os.path.isfile(os.path.join(base, 'intro_stalker.ogm')):
            src = base
            break
    else:
        die('no intro_stalker.ogm under ' + args[0])
    n = 0
    for m in HD_MOVIES:
        f = os.path.join(src, m + '.ogm')
        if not os.path.isfile(f):
            die('missing HD movie ' + f)
        put(f, os.path.join(MEDIA, 'hd', 'textures', 'intro_hd', m + '.ogm')); n += 1
    print('extract-hd done:', n, 'movies in', os.path.join(MEDIA, 'hd'))


def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def stage_all():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    hd = os.path.join(MEDIA, 'hd')
    if os.path.isdir(hd):
        shutil.copytree(hd, os.path.join(STAGE, 'hd'))
    eng = os.path.join(MEDIA, 'eng_raw')
    rus = os.path.join(MEDIA, 'rus_raw')
    # movies are the same in every language: taken from the Steam extract
    for m in MOVIES:
        src = os.path.join(eng, 'textures', 'intro', m + '.ogm')
        if not os.path.isfile(src):
            die('missing ' + src + ' (run extract first)')
        put(src, os.path.join(STAGE, 'movies', 'textures', 'intro', m + '.ogm'))
    for key, root in (('voice_rus', rus), ('voice_eng', eng)):
        for t in TRACKS:
            l = os.path.join(root, VIDEO_DIR, t + '_l.ogg')
            r = os.path.join(root, VIDEO_DIR, t + '_r.ogg')
            if not (os.path.isfile(l) and os.path.isfile(r)):
                die('missing %s track %s' % (key, t))
            d = os.path.join(STAGE, key, VIDEO_DIR)
            put(l, os.path.join(d, t + '_l.ogg'))
            put(r, os.path.join(d, t + '_r.ogg'))
            put(l, os.path.join(d, t + '.ogg'))
        for rel in SINGLES:
            src = os.path.join(root, rel.replace(BS, os.sep))
            if not os.path.isfile(src):
                die('missing ' + src)
            put(src, os.path.join(STAGE, key, rel.replace(BS, os.sep)))


def read_index(path):
    """Entries of a db written by tools\\pack.py: [(name, real, stored, crc, ptr)]."""
    size = os.path.getsize(path)
    ents = []
    with open(path, 'rb') as f:
        pos = 0
        while pos < size:
            f.seek(pos)
            cid, csz = struct.unpack('<II', f.read(8))
            if cid & 0x7fffffff == 1:
                raw = f.read(csz)
                i = 0
                while i < len(raw):
                    bs, rs, cs, crc = struct.unpack_from('<HIII', raw, i)
                    name = raw[i + 14:i + bs - 2].decode('cp1251')
                    ptr = struct.unpack_from('<I', raw, i + bs - 2)[0]
                    ents.append((name, rs, cs, crc, ptr))
                    i += bs + 2
                break
            pos += 8 + csz
    return ents


def lua_unescape(s):
    return s.replace(BS * 2, BS)


def collect_probes():
    """All `need = { tex = {...}, snd = {...} }` strings of the scene packages, plus the endings (built by need_for) and the
    <sound> / video texture names of the movie tutorial blocks."""
    probes = []   # (kind, relative name with extension as the script probes it, where)
    for pkg in sorted(os.listdir(os.path.join(REPO, 'patches'))):
        if not pkg.startswith('cutscenes_pkg_'):
            continue
        sdir = os.path.join(REPO, 'patches', pkg, 'gamedata', 'scripts')
        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith('.script'):
                continue
            text = open(os.path.join(sdir, fn), encoding='utf-8', errors='replace').read()
            consts = dict(re.findall(r'local (\w+)\s*=\s*"([^"]*)"', text))
            for m in re.finditer(r'need\s*=\s*\{', text):
                depth, j = 1, m.end()
                while j < len(text) and depth:
                    depth += {'{': 1, '}': -1}.get(text[j], 0)
                    j += 1
                block = text[m.end():j - 1]
                for kind in ('tex', 'snd'):
                    for km in re.finditer(kind + r'\s*=\s*\{([^}]*)\}', block):
                        for expr in km.group(1).split(','):
                            expr = expr.strip()
                            if not expr:
                                continue
                            # "literal"  or  CONST .. ".ogg"
                            parts = [p.strip() for p in expr.split('..')]
                            val = ''
                            for p in parts:
                                if p.startswith('"'):
                                    val += lua_unescape(p.strip('"'))
                                elif p in consts:
                                    val += lua_unescape(consts[p])
                                else:
                                    val = None
                                    break
                            if val:
                                probes.append((kind, val, pkg + '/' + fn))
            if fn == 'coop_scn_endings.script':
                for key in re.findall(r'key = "(\w+)"', text):
                    probes.append(('tex', 'ui' + BS + 'final_' + key + '.ogm', pkg + '/' + fn + ' (need_for)'))
                    probes.append(('snd', 'intro' + BS + 'final_' + key + '.ogg', pkg + '/' + fn + ' (need_for)'))
    # tutorial blocks: <sound> of video items and the video textures
    cdirs = [os.path.join(REPO, 'patches', 'cutscenes_core', 'gamedata', 'configs', 'ui')]
    for pkg in sorted(os.listdir(os.path.join(REPO, 'patches'))):
        if pkg.startswith('cutscenes_pkg_'):
            cdirs.append(os.path.join(REPO, 'patches', pkg, 'gamedata', 'configs', 'ui'))
    for cd in cdirs:
        if not os.path.isdir(cd):
            continue
        for fn in sorted(os.listdir(cd)):
            if not (fn.startswith('coop_scn_') or fn == 'ui_soc_scenes.xml'):
                continue
            text = open(os.path.join(cd, fn), encoding='utf-8', errors='replace').read()
            for m in re.finditer(r'<item type="video">(.*?)</item>', text, re.S):
                blk = m.group(1)
                for s in re.findall(r'<sound>\s*([^<\s]+)\s*</sound>', blk):
                    probes.append(('xsnd', s + '.ogg', fn + ' <sound>'))
                for t in re.findall(r'<texture[^>]*>\s*([^<\s]+)\s*</texture>', blk):
                    probes.append(('xtex', t + '.ogm', fn + ' video texture'))
    return probes


def addon_files(addon):
    """Lower-case names of every file inside the db members of coop.addon (read only)."""
    sys.path.insert(0, TOOLS)
    import xdb
    names = set()
    mem = xdb.tar_members(addon)
    with open(addon, 'rb') as f:
        for name, (off, size) in mem.items():
            if '.db' in name.lower():
                for e in xdb.index(f, off, size):
                    names.add(e[0].lower())
    return names


def cmd_build(args):
    addon = None
    i = 0
    while i < len(args):
        if args[i] == '--addon':
            addon = args[i + 1]; i += 1
        elif args[i] == '--verbose':
            pass
        else:
            die('unknown option ' + args[i])
        i += 1
    stage_all()
    os.makedirs(OUT, exist_ok=True)
    for dbn, key in DBS.items():
        out = os.path.join(OUT, dbn)
        subprocess.check_call([sys.executable, os.path.join(TOOLS, 'pack.py'), os.path.join(STAGE, key), out, '--no-compress', '--quiet'])
        r = subprocess.call([sys.executable, os.path.join(TOOLS, 'verify_db.py'), out, os.path.join(STAGE, key)])
        if r != 0:
            die('verify_db failed for ' + dbn)
    # inventory
    contents = {}
    lines = []
    total = 0
    for dbn in DBS:
        p = os.path.join(OUT, dbn)
        sz = os.path.getsize(p)
        total += sz
        lines.append('%s  %d bytes (%.1f MB)' % (dbn, sz, sz / 1048576.0))
        for name, rs, cs, crc, ptr in read_index(p):
            if name.endswith(BS):
                continue
            if rs != cs:
                die('%s: %s is compressed, the installer needs raw entries' % (dbn, name))
            contents.setdefault(dbn, []).append((name, rs))
            lines.append('    %s  %d' % (name, rs))
    lines.append('')
    lines.append('movies + one voice: %.1f MB; movies + both voices: %.1f MB' % (
        (os.path.getsize(os.path.join(OUT, 'zz_soc_cutscenes.db')) + os.path.getsize(os.path.join(OUT, 'zz_soc_cutscenes_voice_eng.db'))) / 1048576.0,
        total / 1048576.0))
    open(os.path.join(HERE, 'MANIFEST.txt'), 'w', encoding='utf-8', newline='\n').write(
        'Cutscene pack contents (generated by build_cutscene_pack.py build)\n\n' + '\n'.join(lines) + '\n')
    print('\n'.join(l for l in lines if not l.startswith('    ')))

    # probe check: every need of the scene packages must be satisfied by this pack (+ the mod when --addon is given)
    mod = addon_files(addon) if addon else set()
    for lang in ('voice_rus', 'voice_eng'):
        have = set()
        for dbn in ('zz_soc_cutscenes.db', 'zz_soc_cutscenes_' + lang + '.db'):
            for name, rs in contents[dbn]:
                have.add(name.lower())
        bad = 0
        seen = set()
        for kind, rel, where in collect_probes():
            full = ('textures' if kind in ('tex', 'xtex') else 'sounds') + BS + rel
            full = full.lower()
            if (kind, full) in seen:
                continue
            seen.add((kind, full))
            if full in have:
                src = 'pack'
            elif full in mod:
                src = 'mod'
            else:
                src = 'MISSING'
                bad += 1
            if src == 'MISSING' or '--verbose' in sys.argv:
                print('  [%s] %-8s %-4s %s   (%s)' % (lang, src, kind, rel, where))
        print('probe check %s: %d probes, %d missing' % (lang, len(seen), bad))
        if bad and addon:
            print('probe check FAILED for', lang, bad, 'missing')
        elif bad:
            print('probe check for %s: %d probes are not in the pack (run with --addon to count the mod files)' % (lang, bad))
    shutil.rmtree(STAGE, ignore_errors=True)        # the staged copy is not needed any more (disk space: the HD movies are 1.3 GB)
    # player zip: archives + installer + README (out\SoC_COOP_cutscene_pack.zip)
    import zipfile
    zp = os.path.join(OUT, 'SoC_COOP_cutscene_pack.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for dbn in DBS:
            z.write(os.path.join(OUT, dbn), dbn)
        for fn in ('install_cutscenes.bat', 'install_cutscenes.ps1', 'README_cutscenes.txt'):
            z.write(os.path.join(HERE, fn), fn)
    print('zip: %s (%.1f MB)' % (zp, os.path.getsize(zp) / 1048576.0))
    print('build ok; archives in', OUT)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('extract', 'extract-hd', 'build'):
        sys.exit('usage: build_cutscene_pack.py extract --ru-sounds DIR | extract-hd DIR | build [--addon coop.addon]   (see the comment at the top)')
    {'extract': cmd_extract, 'extract-hd': cmd_extract_hd, 'build': cmd_build}[sys.argv[1]](sys.argv[2:])


if __name__ == '__main__':
    main()
