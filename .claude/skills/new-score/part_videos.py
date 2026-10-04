#!/usr/bin/env python3
"""Build per-part MP4s from a MuseScore video export.
Usage: part_videos.py <video.mp4> <piece_dir> <outdir>
Writes full.mp4 and <part>.mp4 (all with faststart for web streaming).
Replaces the video's audio with <piece_dir>/<part>.mp3 (and full.mp3), and cuts the
intro (title screen), whose length is measured by cross-correlating full.mp3 with the video's audio."""
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
if corr < 0.9:
    # The correlation ceiling depends on how the two exports were rendered: a video made by a
    # different MuseScore build (or a different audio engine) re-synthesises the same performance
    # with different timbre, so a correct pairing can score ~0.8. What actually proves the pairing
    # is that the offset stays put: unrelated takes drift apart within seconds, and a different
    # score never holds one lag. Fall back to measuring the lag in windows across the whole piece.
    A, B = pcm(video), pcm(f'{pdir}/full.mp3')
    WIN = 15  # seconds of mp3 per window
    offsets = []
    for start in range(0, int(len(B) / SR) - WIN + 1, 30):
        seg_start = max(0, start - 12)  # allow the lag to sit before the window
        seg = A[seg_start * SR:(start + WIN + 5) * SR]
        win = B[start * SR:(start + WIN) * SR]
        m = len(seg) * 2
        cc = np.fft.irfft(np.fft.rfft(seg, m) * np.conj(np.fft.rfft(win, m)))
        # Normalise every lag at once: energy of each len(win) slice of seg, via a running sum.
        cs = np.concatenate(([0.0], np.cumsum(seg**2)))
        den = np.sqrt((cs[len(win):] - cs[:-len(win)]) * (win**2).sum())
        corrs = np.divide(cc[:len(den)], den, out=np.zeros_like(den), where=den > 0)
        k = int(np.argmax(corrs))
        offsets.append((seg_start + k / SR - start, corrs[k]))  # lag of this window, and its correlation
    spread = max((o for o, _ in offsets), default=0) - min((o for o, _ in offsets), default=0)
    worst = min((v for _, v in offsets), default=0)
    print(f'drift check: {len(offsets)} windows, offset spread {spread * 1000:.0f} ms, worst correlation {worst:.3f}',
          file=sys.stderr)
    if not offsets or spread > 0.05 or worst < 0.7:
        sys.exit('Audio does not match the video well; check the exports are from the same score.')
    print('Low correlation, but the offset holds steady across the whole piece, so the audio does match it.',
          file=sys.stderr)

# Cut the intro: start the video at the measured offset, so the MP3s line up from 0.
for mp3 in sorted(glob.glob(f'{pdir}/*.mp3')):
    name = os.path.basename(mp3)[:-4]
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{ms / 1000:.3f}', '-i', video, '-i', mp3, '-map', '0:v', '-map', '1:a',
                    '-vf', CROP, *X264, '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    f'{out}/{name}.mp4'], check=True)
    print(f'{out}/{name}.mp4')
