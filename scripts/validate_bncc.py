"""Validate coverage, provenance, unchanged original records and synchronized artifacts."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
graph = json.loads((ROOT / 'dados/BNCC_Grafo.json').read_text(encoding='utf-8'))
source = (ROOT / 'data.js').read_text(encoding='utf-8')
data = json.loads(source[source.index('{'):].strip().rstrip(';'))
html = (ROOT / 'explorador.html').read_text(encoding='utf-8')
embedded = json.loads(html.split('const DATA=', 1)[1].split(';\nconst $=', 1)[0])
assert embedded == graph, 'Standalone explorer differs from downloadable graph'
assert len(graph['nodes']) == len(data['nodes']) == 946
assert len({n['id'] for n in graph['nodes']}) == 946
assert all(n['documented'] and n['records'] and n['text'] for n in graph['nodes'])
assert sum(len(n['records']) for n in graph['nodes']) == 994
assert graph['metadata'] == data['metadata']
def compact_edges(edges):
    return [{**e, 'evidence': [{k: v for k, v in ev.items() if k != 'raw'} for ev in e['evidence']]} for e in edges]
assert compact_edges(graph['edges']) == data['edges']
assert compact_edges(graph['unconfirmed_edges']) == data['unconfirmed_edges']
ui = {n['id']: n for n in data['nodes']}
counts = {'original_records': 0, 'official_added': 0, 'review_records': 0}
for n in graph['nodes']:
    assert n['text'] == ui[n['id']]['text']
    assert len(n['records']) == len(ui[n['id']]['records'])
    for r, u in zip(n['records'], ui[n['id']]['records']):
        if 'source_kind' not in r:
            counts['original_records'] += 1
            continue
        assert all(r[k] for k in ('text', 'theme', 'objectives', 'competencies', 'comment', 'source_url', 'source_note'))
        assert r['fields']['D']['value'] == u['text']
        assert r['fields']['F']['value'] == u['objectives']
        assert r['fields']['G']['value'] == u['competencies']
        assert r['fields']['I']['value'] == u['comment']
        assert not n['focal'] and not n['own_classifications']
        assert r['row'] is None
        assert '\ufffd' not in json.dumps(r, ensure_ascii=False)
        if r['source_kind'] == 'official_bncc':
            counts['official_added'] += 1
            assert r['source_pdf_page'] == r['source_page'] + 2
            assert r['source_url'].endswith(f"#page={r['source_pdf_page']}")
            assert 'Orientação pedagógica elaborada' in r['comment']
            assert r['classification'] == 'BNCC oficial'
        else:
            counts['review_records'] += 1
            assert n['official_status'] == 'unresolved_reference'
assert counts == {'original_records': 471, 'official_added': 520, 'review_records': 3}, counts
ids = set(ui)
unresolved = {n['id'] for n in data['nodes'] if n.get('official_status') == 'unresolved_reference'}
for e in graph['edges']:
    assert e['source'] in ids and e['target'] in ids
    assert not ({e['source'], e['target']} & unresolved)
assert len(graph['edges']) == 3063
assert len(graph['unconfirmed_edges']) == 4
# The supplied workspace also contains the original extraction, when available.
original_path = ROOT.parent / 'BNCC_Grafo.json'
if original_path.exists():
    original = json.loads(original_path.read_text(encoding='utf-8'))
    old = {n['id']: n for n in original['nodes']}
    assert all(n['records'] == old[n['id']]['records'] for n in graph['nodes'] if old[n['id']]['records'])
    key = lambda e: (e['source'], e['target'], e['type'])
    current = graph['edges'] + graph['unconfirmed_edges']
    assert sorted(map(key, original['edges']), key=str) == sorted(map(key, current), key=str)
    print('All 471 original records and all 3067 original relations preserved.')
extract_path = ROOT / 'tmp/bncc/extracted.json'
if extract_path.exists():
    official = json.loads(extract_path.read_text(encoding='utf-8'))
    for n in graph['nodes']:
        for r in n['records']:
            if r.get('source_kind') == 'official_bncc':
                assert r['text'] == official[n['id']][0]['text']
                assert r['source_page'] == official[n['id']][0]['page']
    assert ids - set(official) == unresolved
    print('All 520 added texts and page references match official PDF extraction.')
print(json.dumps(dict(**counts, codes_with_records=946, codes_without_records=0, confirmed_relations=3063, review_relations=4)))
