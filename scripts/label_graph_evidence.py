"""Store skill codes in graph evidence while keeping the workbook map separate."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
graph_path = ROOT / 'dados/BNCC_Grafo.json'
graph = json.loads(graph_path.read_text(encoding='utf-8'))
refs = json.loads((ROOT / 'dados/source_references.json').read_text(encoding='utf-8'))
cells, rows = refs.get('cells', {}), refs.get('rows', {})
sheet_names = sorted({key.rsplit('!', 1)[0] for key in cells}, key=len, reverse=True)
location_re = re.compile('(' + '|'.join(re.escape(sheet) for sheet in sheet_names) + r')!([A-Z]+\d+(?:\+[A-Z]+\d+)*)')

def label(location):
    value = str(location or '')
    if '!' not in value:
        return value
    sheet, cell = value.split('!', 1)
    codes = []
    for part in cell.split('+'):
        part = part.strip()
        row = re.search(r'\d+', part)
        code = cells.get(f'{sheet}!{part}') or rows.get(f'{sheet}#{row.group(0)}' if row else '')
        if code and code not in codes:
            codes.append(code)
    return ' + '.join(codes) or value

def replace_locations(value):
    if not isinstance(value, str):
        return value
    return location_re.sub(lambda match: label(f'{match.group(1)}!{match.group(2)}'), value)

def walk(value, path=''):
    if path.startswith('/metadata/source_references'):
        return value
    if isinstance(value, dict):
        return {key: walk(item, f'{path}/{key}') for key, item in value.items()}
    if isinstance(value, list):
        return [walk(item, f'{path}/{index}') for index, item in enumerate(value)]
    return replace_locations(value)

for edge in graph['edges'] + graph.get('unconfirmed_edges', []):
    for evidence in edge.get('evidence', []):
        if evidence.get('location'):
            evidence['location'] = label(evidence['location'])

graph = walk(graph)

graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
data_path = ROOT / 'data.js'
data_source = data_path.read_text(encoding='utf-8')
data = json.loads(data_source[data_source.index('{'):].strip().rstrip(';'))
compact = lambda edges: [{**edge, 'evidence': [{key: value for key, value in evidence.items() if key != 'raw'} for evidence in edge.get('evidence', [])]} for edge in edges]
data['nodes'] = graph['nodes']
data['edges'] = compact(graph['edges'])
data['unconfirmed_edges'] = compact(graph['unconfirmed_edges'])
data_path.write_text('window.BNCC_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
explorer_path = ROOT / 'explorador.html'
explorer = explorer_path.read_text(encoding='utf-8')
start = explorer.index('const DATA=') + len('const DATA=')
end = explorer.index(';\nconst $=', start)
explorer_path.write_text(explorer[:start] + json.dumps(graph, ensure_ascii=False, separators=(',', ':')) + explorer[end:], encoding='utf-8')
print('labelled graph evidence with skill codes')
