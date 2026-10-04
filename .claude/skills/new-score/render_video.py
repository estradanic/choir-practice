#!/usr/bin/env python3
"""Render the score video ourselves (no MuseScore video export) and build full.mp4 + <part>.mp4.
Usage: render_video.py <score.mscz> <piece_dir> <outdir> [--mscore PATH] [--seconds N]
Uses mscz-to-video (CarlGao4's, AGPL; our fork estradanic/mscz-to-video pinned to a commit, run as an external tool and fetched into tools/, gitignored) to draw the
page, an 850x1100 US Letter portrait video with a thin cursor, once. It then muxes each <piece_dir>/<part>.mp3
onto that picture, so the picture starts at 0 and lines up with the MP3s with no intro to cut.
--seconds renders only the first N seconds (for a quick look)."""
import argparse, glob, io, json, os, shutil, subprocess, sys, urllib.request, zipfile

ap = argparse.ArgumentParser()
ap.add_argument('mscz'); ap.add_argument('pdir'); ap.add_argument('out')
ap.add_argument('--mscore', default=shutil.which('mscore4portable') or shutil.which('mscore') or 'musescore')
ap.add_argument('--seconds', type=float)
a = ap.parse_args()

# Our own fork, pinned to a commit, so upstream changes or removal can't affect us.
FORK = 'https://github.com/estradanic/mscz-to-video'
PIN = 'd10f11e370ec29e51226206be1004383fe9f76ee'

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
tool = os.path.join(root, 'tools', 'mscz-to-video')
lib = os.path.join(root, 'tools', 'lib')
if not os.path.exists(os.path.join(tool, 'mscz2video.py')):
    os.makedirs(tool, exist_ok=True)
    for g in (['init', '-q'], ['fetch', '-q', '--depth', '1', FORK, PIN], ['checkout', '-q', 'FETCH_HEAD']):
        subprocess.run(['git', '-C', tool, *g], check=True)
if not os.path.exists(os.path.join(lib, 'webcolors')):  # pure-python dependency, no pip needed
    info = json.load(urllib.request.urlopen('https://pypi.org/pypi/webcolors/json'))
    url = next(u['url'] for u in info['urls'] if u['url'].endswith('.whl'))
    zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read())).extractall(lib)

os.makedirs(a.out, exist_ok=True)
picture = os.path.join(a.out, '_picture.mp4')
env = dict(os.environ, PYTHONPATH=lib)
cmd = ['python3', os.path.join(tool, 'mscz2video.py'), a.mscz, picture,
       '--ffmpeg-path', 'ffmpeg', '--musescore-path', a.mscore,
       '-r', '24', '-s', '850x1100', '-j', str(min(os.cpu_count() or 2, 8)), '--smooth-cursor',
       # A thin violet-blue line. The measure bar is off (alpha 1 is invisible): with alpha 0 the tool
       # skips drawing the note line too. The tool ends the video at the last note press, so ask for
       # extra time and let -shortest below trim to the audio.
       '--bar-alpha', '1', '--note-color', '#8080ff', '--note-alpha', '170',
       '--fixed-note-width', '2.5', '--extra-note-width-ratio', '0', '--end-offset', '10']
if a.seconds: cmd += ['-t', str(a.seconds)]
cmd += ['--', '-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-g', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
with open(os.path.join(a.out, '_render.log'), 'w') as log:
    subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

for mp3 in sorted(glob.glob(f'{a.pdir}/*.mp3')):
    name = os.path.basename(mp3)[:-4]
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', picture, '-i', mp3, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                    f'{a.out}/{name}.mp4'], check=True)
    print(f'{a.out}/{name}.mp4')
os.remove(picture)
