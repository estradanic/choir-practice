#!/usr/bin/env python3
"""Pre-render slowed MP3s (pitch preserved) with ffmpeg's rubberband, into <piece>/speeds/<speed>/<part>.mp3.

Usage: slow_audio.py public/pieces/<slug> [--force]
The site picks these up automatically. Speeds must match SPEEDS in src/pages/pieces/[slug].astro.
"""
import glob, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

SPEEDS = ['0.75', '0.875']
piece = sys.argv[1]
force = '--force' in sys.argv

def render(job):
    src, dst, s = job
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter:a',
                    f'rubberband=tempo={s}:transients=smooth:phase=laminar:window=long:pitchq=quality',
                    '-codec:a', 'libmp3lame', '-b:a', '128k', dst], check=True)
    print(dst)

jobs = []
for src in sorted(glob.glob(os.path.join(piece, '*.mp3'))):
    for s in SPEEDS:
        dst = os.path.join(piece, 'speeds', s, os.path.basename(src))
        if force or not os.path.exists(dst):
            jobs.append((src, dst, s))
with ThreadPoolExecutor(os.cpu_count() or 2) as ex:
    list(ex.map(render, jobs))
