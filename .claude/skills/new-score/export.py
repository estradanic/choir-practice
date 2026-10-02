#!/usr/bin/env python3
"""Export full + per-part MP3s and PDFs from an .mscz via MuseScore CLI.
Usage: export.py <file.mscz> <outdir> [--mscore PATH]
Per-part audio: temp copy with other parts' notes set to play=0, then exports MP3.
Per-part PDFs: only if the score has Parts (-P)."""
import json, os, re, shutil, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

src, out = sys.argv[1], sys.argv[2]
mscore = sys.argv[sys.argv.index('--mscore') + 1] if '--mscore' in sys.argv else shutil.which('mscore4portable') or 'mscore'
os.makedirs(out, exist_ok=True)
tmp = tempfile.mkdtemp(dir=os.environ.get('TMPDIR', '/tmp/opencode'))

def run(*args):
    subprocess.run([mscore, *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)

def slug(s): return re.sub(r'[^a-z0-9]+', '', s.lower())

run('-o', f'{out}/score.pdf', src)
run('-o', f'{out}/full.mp3', src)

ex = os.path.join(tmp, 'x'); zipfile.ZipFile(src).extractall(ex)
mscx_name = next(f for f in os.listdir(ex) if f.endswith('.mscx'))
mscx = os.path.join(ex, mscx_name)
partstaves = {}
nxt = 1
for p in ET.parse(mscx).getroot().iter('Part'):
    t = p.find('trackName')
    name = slug(t.text or '') if t is not None else ''
    if name and p.find('Staff') is not None:
        k = len(p.findall('Staff'))
        partstaves[name] = {str(i) for i in range(nxt, nxt + k)}
    nxt += len(p.findall('Staff'))
parts = list(partstaves)
# Mute by setting <play>0</play> on every note outside the target part.
# (Soloing via audiosettings.json leaks the first part into the first ~20s.)
for name in parts:
    tree = ET.parse(mscx); root = tree.getroot()
    for st in root.iter('Staff'):
        if st.get('id') in partstaves[name] or not list(st.iter('Measure')): continue
        for n in st.iter('Note'):
            if n.find('play') is None: ET.SubElement(n, 'play').text = '0'
    tree.write(mscx, encoding='UTF-8', xml_declaration=True)
    tmpz = os.path.join(tmp, f'{name}.mscz')
    with zipfile.ZipFile(tmpz, 'w', zipfile.ZIP_DEFLATED) as z:
        for r, _, fs in os.walk(ex):
            for f in fs:
                full = os.path.join(r, f); z.write(full, os.path.relpath(full, ex))
    run('-o', f'{out}/{name}.mp3', tmpz)
    zipfile.ZipFile(src).extract(mscx_name, ex)
pdir = os.path.join(tmp, 'pp'); os.makedirs(pdir)
try: run('-P', '-o', f'{pdir}/p.pdf', src)
except Exception: pass
for f in os.listdir(pdir):
    m = re.match(r'p-(.+)\.pdf$', f)
    if m and slug(m.group(1)) in parts: shutil.copy(os.path.join(pdir, f), f'{out}/{slug(m.group(1))}.pdf')
print(json.dumps({'parts': parts}))
shutil.rmtree(tmp)
