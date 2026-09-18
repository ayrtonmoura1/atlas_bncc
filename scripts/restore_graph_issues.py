"""Restore issue-to-skill associations from the previous validated graph."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
old_source = subprocess.check_output(['git', '-C', str(ROOT / 'tmp/site-publish'), 'show', '82498d1:data.js'])
old_text = old_source.decode('utf-8')
old = json.loads(old_text[old_text.index('{'):].strip().rstrip(';'))
graph_path = ROOT / 'dados/BNCC_Grafo.json'
graph = json.loads(graph_path.read_text(encoding='utf-8'))
issues = {node['id']: node.get('issues', []) for node in old['nodes'] if node.get('issues')}
for node in graph['nodes']:
    node['issues'] = issues.get(node['id'], [])
graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'restored issues for {len(issues)} skills')
