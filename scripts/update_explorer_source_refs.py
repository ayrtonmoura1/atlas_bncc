"""Update the standalone explorer to display workbook skill codes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'explorador.html'
html = path.read_text(encoding='utf-8')

needle = "const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));"
helpers = needle + "\nconst SOURCE_REFS=DATA.metadata?.source_references||{};\nconst sourceCode=(sheet,cell)=>[...new Set(String(cell||'').split('+').map(part=>{const key=`${sheet}!${part.trim()}`,row=part.match(/\\d+/)?.[0];return SOURCE_REFS.cells?.[key]||SOURCE_REFS.rows?.[`${sheet}#${row}`];}).filter(Boolean))].join(' + ');\nconst sourceRef=location=>{const value=String(location??''),match=value.match(/^(.+?)!([A-Z]+\\d+(?:\\+[A-Z]+\\d+)*)$/);return match?sourceCode(match[1],match[2])||value:value;};\nconst sourceText=value=>{let output=String(value??'');const sheets=[...new Set(Object.keys(SOURCE_REFS.rows||{}).map(key=>key.slice(0,key.lastIndexOf('#'))))].sort((a,b)=>b.length-a.length).map(sheet=>sheet.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'));if(!sheets.length)return output;return output.replace(new RegExp(`(${sheets.join('|')})!([A-Z]+\\\\d+(?:\\\\+[A-Z]+\\\\d+)?)`,'g'),(all,sheet,cell)=>sourceCode(sheet,cell)||all);};\nconst recordLabel=(r,n)=>r.source_kind==='official_bncc'?`${r.sheet} · p. ${r.source_page}`:r.source_kind==='source_review'?r.sheet:`${r.sheet} · ${SOURCE_REFS.rows?.[`${r.sheet}#${r.row}`]||n?.id||'habilidade'}`;"
if needle not in html:
    raise SystemExit('explorador esc helper not found')
html = html.replace(needle, helpers, 1)
replacements = {
    "e.evidence.map(x=>x.location)": "e.evidence.map(x=>sourceRef(x.location))",
    "e.evidence.map(v=>v.location)": "e.evidence.map(v=>sourceRef(v.location))",
    "${esc(r.sheet)}${r.source_page?' · p. '+r.source_page:r.row?' · linha '+r.row:''}": "${esc(recordLabel(r,n))}",
    "${esc(r.source_note)}": "${esc(sourceText(r.source_note))}",
    "BNCC_Foco.xlsx — aba e linha indicadas acima.": "BNCC_Foco.xlsx — código correspondente à origem na planilha.",
}
for old, new in replacements.items():
    if old not in html:
        raise SystemExit(f'explorer replacement not found: {old}')
    html = html.replace(old, new)
path.write_text(html, encoding='utf-8')
print('updated explorador.html')
