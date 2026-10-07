#!/usr/bin/env python3
"""Guess metadata from an .mscz and find an existing piece with the same title, composer and part count.
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
match = None
for f in glob.glob('public/pieces/*/piece.json'):
    m = json.load(open(f))
    if norm(m.get('title')) == norm(title) and norm(m.get('composer')) == norm(composer) and len(m.get('parts', [])) == len(parts):
        match = os.path.basename(os.path.dirname(f)); break
print(json.dumps({'title': title, 'composer': composer, 'parts': parts, 'existing': match}, indent=1))
