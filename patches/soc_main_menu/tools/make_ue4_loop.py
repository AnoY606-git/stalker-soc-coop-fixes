"""Makes textures\\ui\\socfx_ue4_menu.ogm (Theora, no audio) from a 1080p mp4 as a seamless loop.

Usage: python make_ue4_loop.py <in.mp4> <out.ogm> [width=1280] [fps=20] [overlap seconds=0.5] [video bitrate kbit/s, default 2000]

* The picture is scaled to <width> x <width>*9/16 and <fps> (ffmpeg, lanczos).
* Seamless loop: the last <overlap> seconds of the source are cross faded into the first ones (the clip is shorter by that much, so the
  wrap last frame -> first frame is two consecutive source frames). The cross faded frames are written as a png sequence.
* The Theora encode is done by Blender 4.2 (headless, its own ffmpeg). The ffmpeg 8.0.1 build on this PC writes corrupt Theora packets
  (its own decoder says "Coefficient index overflow" and the engine shows blocky garbage that grows until the next key frame) at every
  quality, speed level and key frame distance tried, so it cannot be used for the encode.
Needs numpy, opencv-python, ffmpeg (for the decode) and Blender 4.2. Source of the picture: "S.T.A.L.K.E.R. UE4 main menu" by
Daniel Swahn / Ivan Sorce (used with the author's permission, logos removed).
"""
import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

BLENDER = r'C:\Program Files\Blender Foundation\Blender 4.2\blender.exe'
src, dst = sys.argv[1], sys.argv[2]
OW = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
FPS = int(sys.argv[4]) if len(sys.argv) > 4 else 20
L = int(round(float(sys.argv[5]) * FPS)) if len(sys.argv) > 5 else FPS // 2
BITRATE = int(sys.argv[6]) if len(sys.argv) > 6 else 2000
OH = OW * 9 // 16
FS = OW * OH * 3
work = tempfile.mkdtemp(prefix='ue4loop_')


def decode():
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-vf', 'scale=%d:%d:flags=lanczos,fps=%d' % (OW, OH, FPS),
                             '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)


def read_frame(p):
    b = p.stdout.read(FS)
    return np.frombuffer(b, np.uint8).reshape(OH, OW, 3) if len(b) == FS else None


p = decode()
N = 0
while read_frame(p) is not None:
    N += 1
p.kill()
M = N - L
print('frames at %d fps: %d, loop frames %d' % (FPS, N, M))

p = decode()
for _ in range(M):
    p.stdout.read(FS)
tail = [read_frame(p).astype(np.float32) for _ in range(L)]
p.kill()

p = decode()
for k in range(M):
    f = read_frame(p)
    if k < L:
        a = k / float(L)
        f = np.clip(tail[k] * (1 - a) + f.astype(np.float32) * a, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(work, 'f%04d.png' % (k + 1)), f)
p.kill()

script = os.path.join(work, 'render.py')
open(script, 'w').write('''import bpy
sc = bpy.context.scene
for o in list(sc.objects):
    bpy.data.objects.remove(o)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = %d, %d, 100
sc.render.fps, sc.render.fps_base = %d, 1
sc.frame_start, sc.frame_end = 1, %d
sc.use_nodes = False
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0
sc.view_settings.gamma = 1
sc.display_settings.display_device = "sRGB"
sc.sequence_editor_create()
files = [{"name": "f%%04d.png" %% (i + 1)} for i in range(%d)]
st = sc.sequence_editor.sequences.new_image("ue4", %r + "/f0001.png", 1, 1)
for i in range(1, %d):
    st.elements.append("f%%04d.png" %% (i + 1))
sc.render.use_sequencer = True
sc.render.image_settings.file_format = "FFMPEG"
sc.render.image_settings.color_mode = "RGB"
ff = sc.render.ffmpeg
ff.format = "OGG"
ff.codec = "THEORA"
ff.constant_rate_factor = "NONE"
ff.video_bitrate = %d
ff.ffmpeg_preset = "GOOD"
ff.gopsize = %d
ff.audio_codec = "NONE"
sc.render.filepath = %r
bpy.ops.render.render(animation=True)
''' % (OW, OH, FPS, M, M, work.replace('\\', '/'), M, BITRATE, FPS, os.path.join(work, 'out_').replace('\\', '/')))
subprocess.check_call([BLENDER, '-b', '--factory-startup', '--python', script], stdout=subprocess.DEVNULL)
outs = [f for f in os.listdir(work) if f.startswith('out_') and f.endswith(('.ogv', '.ogg', '.ogm'))]
assert outs, os.listdir(work)[:5]
shutil.copyfile(os.path.join(work, outs[0]), dst)
r = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-i', dst, '-f', 'null', '-'], capture_output=True, text=True)
print('wrote', dst, os.path.getsize(dst), 'bytes;', 'decodes CLEAN in ffmpeg' if not r.stderr.strip() else 'ffmpeg decode messages: ' + r.stderr.strip()[:300])
shutil.rmtree(work, ignore_errors=True)
sys.exit(0 if not r.stderr.strip() else 1)
