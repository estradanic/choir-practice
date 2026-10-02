#!/usr/bin/env python3
"""Build per-part MP4s from a MuseScore video export.
Usage: part_videos.py <video.mp4> <piece_dir> <outdir>
Writes full.mp4 and <part>.mp4 (all with faststart for web streaming).
Replaces the video's audio with <piece_dir>/<part>.mp3 (and full.mp3), delayed by the
intro offset, which is measured by cross-correlating full.mp3 with the video's audio."""
import glob, os, subprocess, sys
import numpy as np

video, pdir, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
SR = 8000

# Crop to the sheet-music page (US Letter 8.5:11 portrait) of the 1920x1080 MuseScore
# video export. The pure-white page fills x=542..1373, y=0..1077 (columns 541/1374 are
# antialiased page edges) and does not move: measured identical at t=10/60/110s.
# 832x1078 -> 832/1078 = 0.772 (US Letter is 8.5/11 = 0.773); w and h are even.
CROP = 'crop=832:1078:542:0'
X264 = ['-c:v', 'libx264', '-crf', '23', '-preset', 'fast']

def pcm(path, secs=None):
    cmd = ['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(SR)]
    if secs: cmd += ['-t', str(secs)]
    return np.frombuffer(subprocess.run(cmd + ['-f', 's16le', '-'], capture_output=True, check=True).stdout, 'int16').astype(float)

a = pcm(video, 70); b = pcm(f'{pdir}/full.mp3', 60)
n = len(a) * 2
c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)))
i = int(np.argmax(c[:SR * 10]))
corr = c[i] / np.sqrt((a[i:i + len(b)] ** 2).sum() * (b[:len(a) - i] ** 2).sum())
ms = round(i / SR * 1000)
print(f'offset {ms} ms, correlation {corr:.3f}', file=sys.stderr)
if corr < 0.9: sys.exit('Audio does not match the video well; check the exports are from the same score.')

subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vf', CROP, *X264,
                '-c:a', 'copy', '-movflags', '+faststart', f'{out}/full.mp4'], check=True)
print(f'{out}/full.mp4')

for mp3 in sorted(glob.glob(f'{pdir}/*.mp3')):
    name = os.path.basename(mp3)[:-4]
    if name == 'full': continue
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', mp3, '-map', '0:v', '-map', '1:a',
                    '-vf', CROP, *X264, '-movflags', '+faststart', '-af', f'adelay={ms}:all=1', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    f'{out}/{name}.mp4'], check=True)
    print(f'{out}/{name}.mp4')
