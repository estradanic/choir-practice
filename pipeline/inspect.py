#!/usr/bin/env python3
"""Guess metadata from an .mscz and list existing pieces that look similar (fuzzy candidates).
Usage: inspect.py <file.mscz>  -> JSON on stdout."""
import glob, json, os, re, sys, unicodedata, zipfile
import xml.etree.ElementTree as ET

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z0-9]+', '', ''.join(c for c in s if not unicodedata.combining(c)).lower())

z = zipfile.ZipFile(sys.argv[1])
root = ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.mscx'))))
tags = {m.get('name'): (m.text or '').strip() for m in root.iter('metaTag')}
title = tags.get('workTitle') or next((t.text for t in root.iter('text') if t.text), '') or os.path.basename(sys.argv[1])[:-5]
composer = tags.get('composer', '')
parts = [(p.find('trackName').text if p.find('trackName') is not None else '') for p in root.iter('Part') if p.findall('Staff')]
staves = []
for st in root.find('Score').findall('Staff'):
    n = max((sum(1 for v in m.findall('voice') if v.find('Chord') is not None) for m in st.findall('Measure')), default=0)
    staves.append(n)
closed = None
if len(staves) in (2, 3) and any(n >= 2 for n in staves):
    closed = 'closed score: ' + ', '.join(f'staff {i+1} has {n} voice(s)' for i, n in enumerate(staves)) + (
        '. Likely SATB on 2 staves: soprano,alto on the upper staff, tenor,bass on the lower (--voices "soprano,alto" --voices "tenor,bass")' if len(staves) == 2 else '')
elif len(staves) == 2 and len(parts) == 2:
    closed = 'two staves, possibly a closed SATB score (voices may be written as one voice per staff, verify)'
from difflib import SequenceMatcher
def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b: return 0
    return max(SequenceMatcher(None, a, b).ratio(), 0.9 if a in b or b in a else 0)
cands = []
for f in glob.glob('public/pieces/*/piece.json'):
    m = json.load(open(f))
    t, c = sim(m.get('title'), title), sim(m.get('composer'), composer)
    score = round(0.6 * t + 0.4 * c, 2)
    if score >= 0.5:
        cands.append({'slug': os.path.basename(os.path.dirname(f)), 'title': m.get('title'), 'composer': m.get('composer'),
                      'parts': len(m.get('parts', [])), 'partsMatch': len(m.get('parts', [])) == len(parts),
                      'titleSim': round(t, 2), 'composerSim': round(c, 2), 'score': score})
cands.sort(key=lambda c: -c['score'])
print(json.dumps({'title': title, 'composer': composer, 'parts': parts, 'staffVoices': staves, 'closedScoreGuess': closed, 'candidates': cands[:5]}, indent=1))
