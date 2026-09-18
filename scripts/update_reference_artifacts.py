"""Replace workbook cell references in downloadable audit artifacts with skill codes."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
refs = json.loads((ROOT / 'dados/source_references.json').read_text(encoding='utf-8'))
cells = refs.get('cells', {})
rows = refs.get('rows', {})

def label(sheet, cell):
    codes = []
    for part in str(cell or '').split('+'):
        part = part.strip()
        match = re.search(r"\d+", part)
        code = cells.get(f'{sheet}!{part}') or rows.get(f'{sheet}#{match.group(0)}' if match else '')
        if code and code not in codes:
            codes.append(code)
    return ' + '.join(codes)

sheet_names = sorted({key.rsplit('!', 1)[0] for key in cells}, key=len, reverse=True)
location_re = re.compile('(' + '|'.join(re.escape(sheet) for sheet in sheet_names) + r')!([A-Z]+\d+(?:\+[A-Z]+\d+)*)')

def replace_locations(value):
    if not isinstance(value, str):
        return value
    return location_re.sub(lambda match: label(match.group(1), match.group(2)) or match.group(0), value)

def walk(value):
    if isinstance(value, dict):
        return {key: walk(item) for key, item in value.items()}
    if isinstance(value, list):
        return [walk(item) for item in value]
    return replace_locations(value)

csv_path = ROOT / 'dados/BNCC_Relacoes.csv'
with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
    rows_csv = list(csv.DictReader(handle))
with csv_path.open('w', encoding='utf-8-sig', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['origem', 'destino', 'tipo', 'evidencia', 'status'])
    writer.writeheader()
    for row in rows_csv:
        row['evidencia'] = replace_locations(row['evidencia'])
        writer.writerow(row)

json_path = ROOT / 'dados/complementacao_bncc.json'
report = json.loads(json_path.read_text(encoding='utf-8'))
json_path.write_text(json.dumps(walk(report), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

audit_path = ROOT / 'dados/Auditoria.md'
audit_path.write_text(replace_locations(audit_path.read_text(encoding='utf-8')), encoding='utf-8')
print('updated BNCC_Relacoes.csv, complementacao_bncc.json and Auditoria.md')
