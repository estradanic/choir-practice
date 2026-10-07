#!/usr/bin/env python3
"""Export full + per-part MP3s and PDFs from an .mscz via MuseScore CLI.
Usage: export.py <file.mscz> <outdir> [--mscore PATH] [--voices "soprano,alto"]...
Per-part audio: temp copy with other parts' notes set to play=0, then exports MP3.
--voices (one group per staff, score order) splits a closed SATB score into its voices,
naming the parts soprano/alto/... instead of the staff (Women/Men); omit for one part per staff."""
import json, os, re, shutil, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

src, out = sys.argv[1], sys.argv[2]
mscore = sys.argv[sys.argv.index('--mscore') + 1] if '--mscore' in sys.argv else shutil.which('mscore4portable') or 'mscore'


def optvals(flag):
    return [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == flag and i + 1 < len(sys.argv)]


# --voices "soprano,alto" --voices "tenor,bass": one group per staff, in score order, naming that
# staff's voices (closed SATB score) instead of the staff itself. Omit the flag for one part per staff.
voice_groups = [[n.strip() for n in v.split(',') if n.strip()] for v in optvals('--voices')]
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
raw, nxt = [], 1
for p in ET.parse(mscx).getroot().iter('Part'):
    staves = p.findall('Staff')
    t = p.find('trackName')
    ln = next(p.iter('longName'), None)
    track = slug(t.text or '') if t is not None else ''
    inst = slug(ln.text or '') if ln is not None else ''
    if staves:
        raw.append((track, inst, {str(i) for i in range(nxt, nxt + len(staves))}))
    nxt += len(staves)

# Parts can share a trackName (a Descant copied from Soprano, with only the instrument
# renamed, leaves trackName='Soprano' on both). Keying on trackName alone silently drops
# one of them: its staff is never muted, so it leaks into every other part's export.
# Resolve duplicates by preferring the instrument name when it is unique, else a suffix.
def tally():
    c = {}
    for track, inst, _ in raw:
        for n in {track, inst} - {''}:
            c[n] = c.get(n, 0) + 1
    return c
counts = tally()
staff_order = [i for _, _, ids in raw for i in sorted(ids, key=int)]
partstaves = {}
if voice_groups:
    if len(voice_groups) != len(staff_order):
        sys.exit(f'--voices: one group per staff needed ({len(staff_order)} staves), got {len(voice_groups)}')
    for stid, names in zip(staff_order, voice_groups):
        for vi, name in enumerate(names):
            if name in partstaves:
                sys.exit(f'--voices: duplicate part name {name!r}')
            partstaves[name] = ({stid}, None) if len(names) == 1 else ({stid}, vi)
else:
    for track, inst, ids in raw:
        base = track or inst
        name = inst if counts[base] > 1 and inst and inst != base and counts[inst] == 1 else base
        n = 1
        while name in partstaves:
            n += 1
            name = f'{base}{n}'
        partstaves[name] = (ids, None)
parts = list(partstaves)
# Mute by setting <play>0</play> on every note outside the target part.
# (Soloing via audiosettings.json leaks the first part into the first ~20s.)
def mute(el):
    for n in el.iter('Note'):
        if n.find('play') is None: ET.SubElement(n, 'play').text = '0'

for name in parts:
    tree = ET.parse(mscx); root = tree.getroot()
    staves, voice = partstaves[name]
    for st in root.iter('Staff'):
        if not list(st.iter('Measure')): continue
        if st.get('id') not in staves: mute(st); continue
        if voice is None: continue
        for m in st.findall('Measure'):
            vs = [c for c in m if c.tag == 'voice'] or [m]
            for i, v in enumerate(vs):
                if i != voice: mute(v)
    tree.write(mscx, encoding='UTF-8', xml_declaration=True)
    tmpz = os.path.join(tmp, f'{name}.mscz')
    with zipfile.ZipFile(tmpz, 'w', zipfile.ZIP_DEFLATED) as z:
        for r, _, fs in os.walk(ex):
            for f in fs:
                full = os.path.join(r, f); z.write(full, os.path.relpath(full, ex))
    run('-o', f'{out}/{name}.mp3', tmpz)
    zipfile.ZipFile(src).extract(mscx_name, ex)
# Record the score's staff order, so the site lists tracks in the order the staves appear.
pj = os.path.join(out, 'piece.json')
if os.path.exists(pj):
    with open(pj) as f:
        meta = json.load(f)
    meta['parts'] = parts
    with open(pj, 'w') as f:
        json.dump(meta, f, indent=2)
        f.write('\n')
print(json.dumps({'parts': parts}))
shutil.rmtree(tmp)
