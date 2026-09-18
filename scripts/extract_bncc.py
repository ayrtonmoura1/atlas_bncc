"""Extract skill blocks from the official MEC PDF, retaining page and geometry."""
import json
import re
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
doc = fitz.open(ROOT / 'tmp/bncc/oficial.pdf')
pattern = re.compile(r'\(((?:EF\d{2}[A-Z]{2}\d{2}|EI\d{2}[A-Z]{2}\d{2}|EM\d{2}[A-Z]{2,3}\d{2,3}))\)')
found = {}
for page_no, page in enumerate(doc):
    for block in page.get_text('blocks'):
        text = block[4]
        matches = list(pattern.finditer(text))
        for i, match in enumerate(matches):
            value = text[match.end():matches[i+1].start() if i+1 < len(matches) else len(text)]
            value = re.sub(r'\s+', ' ', value.replace('\u00ad', '')).strip()
            if match[1].startswith('EM13LP'):
                value = re.sub(r'(?<=[.])\s+[\d, e]+$', '', value)
            if value:
                found.setdefault(match[1], []).append(dict(text=value, pdf_page=page_no+1, page=page_no-1, bbox=list(block[:4])))
# Prefer curricular tables over illustrative mentions in the introductory section.
for code, occurrences in found.items():
    occurrences.sort(key=lambda item: (item['pdf_page'] < 90 if code.startswith('EF') else False, item['pdf_page']))
graph = json.loads((ROOT / 'dados/BNCC_Grafo.json').read_text(encoding='utf-8'))
missing = [n['id'] for n in graph['nodes'] if not n['records']]
(ROOT / 'tmp/bncc/extracted.json').write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding='utf-8')
print('Missing official codes:', [c for c in missing if c not in found])
print('Multiple occurrences:', {c: len(found[c]) for c in missing if len(found.get(c, [])) > 1})
print('Suspicious endings:', [(c, v[0]['text'][-100:]) for c in missing if (v := found.get(c)) and not v[0]['text'].endswith(('.', ')', ' etc.'))])
print('Shortest:', sorted([(c, len(found[c][0]['text'])) for c in missing if c in found], key=lambda x: x[1])[:15])
