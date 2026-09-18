"""Complete the Atlas from official MEC text without changing original records."""
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://basenacionalcomum.mec.gov.br/images/BNCC_EI_EF_110518_versaofinal_site.pdf'
PDF = ROOT / 'tmp/bncc/oficial.pdf'
doc = fitz.open(PDF)
official = json.loads((ROOT / 'tmp/bncc/extracted.json').read_text(encoding='utf-8'))
graph_path = ROOT / 'dados/BNCC_Grafo.json'
graph = json.loads(graph_path.read_text(encoding='utf-8'))
data_path = ROOT / 'data.js'
source = data_path.read_text(encoding='utf-8')
data = json.loads(source[source.index('{'):].strip().rstrip(';'))
by_id = {n['id']: n for n in data['nodes']}
# Make regeneration safe without touching the 471 original spreadsheet records.
for target in [graph, data]:
    target['issues'] = [i for i in target['issues'] if i['type'] != 'Código ausente na BNCC oficial']
    for node in target['nodes']:
        node['records'] = [r for r in node['records'] if r.get('source_kind') not in ('official_bncc', 'source_review')]
        if 'issues' in node:
            node['issues'] = [i for i in node['issues'] if i['type'] != 'Código ausente na BNCC oficial']

def clean(value):
    return re.sub(r'\s+', ' ', value).strip()

def lines(page):
    return [dict(text=clean(''.join(s['text'] for s in line['spans'])), bbox=line['bbox'], font=line['spans'][0]['font'])
            for block in page.get_text('dict')['blocks'] for line in block.get('lines', []) if line['spans']]

page_lines = [lines(page) for page in doc]
EI = {'ET': 'Espaços, tempos, quantidades, relações e transformações', 'EO': 'O eu, o outro e o nós',
      'CG': 'Corpo, gestos e movimentos', 'EF': 'Escuta, fala, pensamento e imaginação', 'TS': 'Traços, sons, cores e formas'}
CE_PAGES = {'LP': 87, 'MA': 267, 'CI': 324, 'GE': 366, 'HI': 402}

def theme_for(node, item):
    code = node['id']
    p = item['pdf_page'] - 1
    y = item['bbox'][1]
    if code.startswith('EI'):
        return EI[node['component_code']]
    if code.startswith('EM') and node['component_code'] != 'LP':
        return f"{node['component']} — competência específica {code[7]}"
    if node['component_code'] == 'LP':
        candidates = []
        for pn in [p-1, p]:
            for line in page_lines[pn]:
                if line['bbox'][1] <= y+3 and (line['text'].startswith('CAMPO ') or line['text'].startswith('TODOS OS CAMPOS')):
                    candidates.append(line)
        if candidates:
            # Field names may wrap over two lines, but their first line identifies the field.
            return max(candidates, key=lambda line: line['bbox'][1])['text'].split(' – ')[0].split(' — ')[0].replace(' (Continuação)', '').capitalize()
        raise ValueError(f'Campo não localizado: {code}')
    # The official fundamental tables are facing-page spreads with aligned rows.
    candidates = [line for line in page_lines[p-1] if 145 < line['bbox'][1] <= y+3 and line['bbox'][0] < 150 and 'Bold' in line['font']]
    if not candidates:
        raise ValueError(f'Unidade não localizada: {code}')
    last = candidates[-1]
    group = [last]
    for line in reversed(candidates[:-1]):
        if group[0]['bbox'][1] - line['bbox'][1] < 16:
            group.insert(0, line)
        else:
            break
    # Include wrapped continuation lines below the first skill baseline.
    for line in page_lines[p-1]:
        if line['bbox'][0] < 150 and 'Bold' in line['font'] and 0 < line['bbox'][1]-group[-1]['bbox'][1] < 16:
            group.append(line)
    return ' '.join(line['text'] for line in group)

def competencies_for(node, item):
    code = node['id']
    if code.startswith('EI'):
        return 'Direitos de aprendizagem e desenvolvimento: conviver, brincar, participar, explorar, expressar e conhecer-se (BNCC, p. 38). Os objetivos da Educação Infantil são organizados por campos de experiências; não recebem códigos CE/CA/CG individuais.'
    if code.startswith('EM'):
        if node['component_code'] != 'LP':
            number = code[7]
        else:
            y = item['bbox'][1]
            nums = [line['text'] for line in page_lines[item['pdf_page']-1] if line['bbox'][0] > 440 and abs(line['bbox'][1]-y) < 3 and re.fullmatch(r'[\d, e]+', line['text'])]
            if not nums:
                raise ValueError(f'Competência EM não localizada: {code}')
            number = ', '.join(nums)
        return f"Competência(s) específica(s) da área: {number}. Associação expressa no quadro oficial da BNCC, p. {item['page']}. Competências gerais da Educação Básica: quadro da BNCC, pp. 9–10; não há numeração CG por habilidade nesse quadro."
    page = CE_PAGES[node['component_code']]
    return f"Referencial: competências específicas de {node['component']} (BNCC, p. {page}) e competências gerais da Educação Básica (pp. 9–10). A BNCC não apresenta uma correspondência numérica CE/CA/CG para esta habilidade; essa associação exige planejamento pedagógico e não foi atribuída como se fosse oficial."

GUIDANCE = {
    'LP': ('Selecionar textos reais adequados ao campo de atuação e ao ano/faixa de anos. Modelar a leitura ou a produção e propor uma realização orientada seguida de uma realização com maior autonomia.', 'Registrar trechos, falas ou produções que evidenciem a ação descrita no enunciado; retomar com o estudante suas escolhas e os efeitos de sentido.'),
    'MA': ('Propor uma situação-problema vinculada ao conteúdo do enunciado. Permitir representações concretas, desenhos e registros simbólicos, conforme o ano, e comparar estratégias de resolução.', 'Observar o procedimento e a justificativa, além do resultado. Pedir que o estudante explique sua estratégia e verifique se a resposta é coerente com o problema.'),
    'MAT': ('Propor a análise de um problema com dados e condições explícitos. Articular representações numéricas, algébricas, geométricas ou gráficas pertinentes ao enunciado e discutir as hipóteses utilizadas.', 'Avaliar a escolha da representação, o desenvolvimento da resolução e a interpretação do resultado no contexto; solicitar justificativas e verificação dos limites da solução.'),
    'CI': ('Partir de uma pergunta investigável ligada ao fenômeno do enunciado. Levantar ideias iniciais e usar observações, modelos, registros ou fontes científicas adequadas à idade para confrontá-las.', 'Recolher explicações e registros do estudante, observando se distingue observação de interpretação e se utiliza evidências para sustentar a conclusão.'),
    'CNT': ('Organizar uma investigação ou análise de caso coerente com o fenômeno do enunciado. Comparar dados, modelos e explicações científicas e discutir as condições e limites de sua aplicação.', 'Avaliar a consistência dos argumentos com as evidências, o uso de conceitos científicos e a comunicação dos resultados e de suas limitações.'),
    'GE': ('Relacionar o recorte espacial do enunciado aos lugares de vivência. Usar mapas, imagens, relatos ou dados pertinentes e comparar as escalas necessárias para compreender o fenômeno.', 'Solicitar uma representação ou explicação geográfica, observando a localização, as relações entre sociedade e natureza e o uso das informações das fontes.'),
    'HI': ('Selecionar fontes históricas pertinentes ao período e aos sujeitos do enunciado. Situar autoria, tempo e contexto e confrontar perspectivas, evitando tratar uma fonte isolada como retrato completo do passado.', 'Solicitar uma explicação apoiada nas fontes, verificando a contextualização, as mudanças e permanências e o reconhecimento de diferentes sujeitos históricos.'),
    'EI': ('Organizar brincadeiras e interações que ofereçam oportunidades de realizar a ação do objetivo, com materiais acessíveis e espaço para iniciativas das crianças.', 'Documentar falas, gestos, escolhas e descobertas em registros de observação e portfólios. Acompanhar percursos sem transformar o objetivo em prova ou requisito de ingresso no Ensino Fundamental.')
}

invalid = {
    'EF13LP03': ('A faixa EF13 não identifica um bloco de habilidades de Língua Portuguesa na BNCC. A referência aparece em 1º ano LP!H12, associada a EF01LP22. Não há evidência suficiente para escolher um código substituto.', None),
    'EM02MA18': ('O código não segue o padrão do Ensino Médio. A menção em 3º ano MT!I13 trata de medidas de tempo de anos anteriores. EF02MA18 é uma possível correção, coerente com o assunto, mas essa hipótese não substitui a referência original.', 'EF02MA18'),
    'EM08MA18': ('O código não segue o padrão do Ensino Médio. As referências em 9 ano MT!B9 e B12 tratam de habilidades de geometria. EF08MA18 é uma possível correção, coerente com o assunto, mas essa hipótese não substitui a referência original.', 'EF08MA18')
}

additions = []
for node in graph['nodes']:
    if node['records']:
        continue
    code = node['id']
    ui_node = by_id[code]
    if code in invalid:
        explanation, candidate = invalid[code]
        text = 'Código não localizado na BNCC oficial. ' + explanation
        loc = '; '.join(m['sheet']+'!'+m['cell'] for m in node['mentions'])
        record = dict(sheet='Revisão da referência original', row=None, text=text, theme='Inconsistência de código na fonte', classification='Referência em revisão',
                      objectives='Este registro documenta uma inconsistência da planilha, não uma habilidade oficial. Consulte a origem e a hipótese indicada antes de utilizá-lo no planejamento.',
                      competencies='Não atribuídas: o código não identifica uma habilidade oficial.',
                      comment='Análise editorial: '+explanation, commentCell='', rawPrior='', rawRelated='',
                      source_kind='source_review', source_url=URL, source_page=None, source_pdf_page=None,
                      source_note='BNCC_Foco.xlsx: '+loc, candidate_code=candidate)
        issue = dict(type='Código ausente na BNCC oficial', source=loc, value=explanation)
        ui_node['issues'].append(issue)
        graph['issues'].append(issue)
        data['issues'].append(issue)
        node['official_status'] = ui_node['official_status'] = 'unresolved_reference'
    else:
        item = official[code][0]
        theme = theme_for(node, item)
        competencies = competencies_for(node, item)
        steps, assessment = GUIDANCE['EI' if code.startswith('EI') else node['component_code']]
        record = dict(sheet='BNCC oficial · MEC (2018)', row=None, text=item['text'], theme=theme, classification='BNCC oficial',
                      objectives='Objetivo curricular (enunciado oficial):\n• '+item['text'],
                      competencies=competencies,
                      comment=f"Orientação pedagógica elaborada para este atlas; não é transcrição do MEC nem dos Mapas de Foco.\n\nFoco: {theme}.\n\n{steps}\n\nAcompanhamento: {assessment}\n\nCritério de planejamento: preservar os verbos, os conteúdos e as condições de realização de {code}. Adequar apoios e acessibilidade à turma e usar as evidências para decidir as retomadas.",
                      commentCell='', rawPrior='', rawRelated='', source_kind='official_bncc', source_url=URL+f"#page={item['pdf_page']}",
                      source_page=item['page'], source_pdf_page=item['pdf_page'],
                      source_note=f"BRASIL. Ministério da Educação. Base Nacional Comum Curricular. Brasília: MEC, 2018. p. {item['page']} (página {item['pdf_page']} do PDF).",
                      competency_source_url=URL+f"#page={40 if code.startswith('EI') else item['pdf_page'] if code.startswith('EM') else CE_PAGES[node['component_code']]+2}")
        node['official_status'] = ui_node['official_status'] = 'verified'
    for target in [node, ui_node]:
        target['text'] = record['text']
        target['documented'] = True
        target['themes'] = [record['theme']]
        # AF/AC/EF are Mapas de Foco classifications, not assigned by the official PDF.
    ui_node['records'] = [record]
    fields = {}
    values = {'A': record['theme'], 'B': '', 'C': code, 'D': record['text'], 'E': record['classification'],
              'F': record['objectives'], 'G': record['competencies'], 'H': '', 'I': record['comment']}
    for column, value in values.items():
        fields[column] = dict(value=value, formatted=value, cell=None, source=record['source_note'])
    node['records'] = [{**record, 'fields': fields, 'comment_column': 'I'}]
    additions.append(dict(id=code, source_kind=record['source_kind'], page=record['source_page'], url=record['source_url'], theme=record['theme']))

# Invalid references stay inspectable but cannot imply confirmed curricular relationships.
for target in [graph, data]:
    uncertain = [e for e in target['edges'] if e['source'] in invalid or e['target'] in invalid]
    target['unconfirmed_edges'] = target.get('unconfirmed_edges', []) + uncertain
    target['edges'] = [e for e in target['edges'] if e not in uncertain]
    meta = target['metadata']
    meta.update(records=sum(len(n['records']) for n in target['nodes']), documented_skills=len(target['nodes']), reference_only=0,
                official_added=520, review_records=3, original_documented_skills=423, original_records=471,
                confirmed_official_skills=943, unconfirmed_relations=len(target['unconfirmed_edges']), issues=len(target['issues']),
                edges_by_type=dict(collections.Counter(e['type'] for e in target['edges'])),
                official_source=dict(title='Base Nacional Comum Curricular', publisher='Ministério da Educação', year=2018, url=URL,
                                     consulted='2026-09-18', sha256=hashlib.sha256(PDF.read_bytes()).hexdigest()))

audit_path = ROOT / 'dados/auditoria.json'
audit = json.loads(audit_path.read_text(encoding='utf-8'))
audit['complementacao_bncc'] = dict(date='2026-09-18', official_added=520, review_records=3,
    codes_with_records=946, codes_without_records=0, original_records_preserved=471,
    confirmed_relations=3063, unconfirmed_relations=4, source=graph['metadata']['official_source'])
data['audit'] = audit
audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
with (ROOT / 'dados/BNCC_Relacoes.csv').open('w', encoding='utf-8-sig', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['origem', 'destino', 'tipo', 'evidencia', 'status'])
    for edges, status in [(graph['edges'], 'confirmada na planilha'), (graph['unconfirmed_edges'], 'em revisão: código ausente na BNCC')]:
        for e in edges:
            writer.writerow([e['source'], e['target'], e['type'], '; '.join(v['location'] for v in e['evidence']), status])
graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
data_path.write_text('window.BNCC_DATA = '+json.dumps(data, ensure_ascii=False, separators=(',', ':'))+';\n', encoding='utf-8')
explorer_path = ROOT / 'explorador.html'
explorer = explorer_path.read_text(encoding='utf-8')
start = explorer.index('const DATA=') + len('const DATA=')
end = explorer.index(';\nconst $=', start)
explorer = explorer[:start] + json.dumps(graph, ensure_ascii=False, separators=(',', ':')) + explorer[end:]
explorer_path.write_text(explorer, encoding='utf-8')
report = dict(official_source=graph['metadata']['official_source'], original_cards=423, official_cards_added=520,
              review_cards=3, codes_with_records=946, codes_without_records=0, additions=additions,
              unconfirmed_relations=graph['unconfirmed_edges'])
(ROOT / 'dados/complementacao_bncc.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
report_md = '''# Complementação das fichas pela BNCC oficial

Conferência em 18/09/2026. Escopo: todos os 946 códigos já presentes no atlas; não representa a inclusão de todas as habilidades de todos os componentes da BNCC.

- 423 habilidades com 471 registros originais preservados integralmente.
- 520 habilidades receberam ficha com enunciado extraído da BNCC oficial.
- 3 referências inconsistentes receberam ficha de revisão, sem inventar enunciado oficial.
- 946 códigos com registro; nenhum código sem ficha. Total: 994 registros.
- 3063 relações permanecem no grafo, incluindo 587 pré-requisitos.
- 4 relações envolvendo códigos inconsistentes foram preservadas em `unconfirmed_edges` e no CSV, identificadas como em revisão. Não geram caminhos confirmados.

## Fonte e método

BRASIL. Ministério da Educação. **Base Nacional Comum Curricular**. Brasília: MEC, 2018. Documento completo, 600 páginas no PDF disponibilizado atualmente pelo MEC, incluindo o Ensino Médio, apesar do nome histórico do arquivo.

Fonte: [BNCC oficial no MEC](SOURCE_URL).

O número de página indicado nas fichas é o impresso no documento. O link utiliza a posição no PDF (página impressa + 2). Enunciados foram extraídos dos blocos das tabelas, preservando a separação entre colunas. Quebras de linha foram normalizadas; números da coluna de competências não foram incorporados ao enunciado. Campos e unidades temáticas foram associados aos quadros oficiais, considerando o alinhamento entre páginas espelhadas.

As novas fichas mantêm as seções de enunciado, campo/unidade, objetivos, competências, comentários e fonte. O objetivo curricular reproduz o enunciado oficial. Os comentários novos são orientações pedagógicas editoriais, explicitamente identificadas. No Ensino Fundamental a BNCC não publica associação CE/CA/CG por habilidade: o campo informa o referencial do componente sem inventar números. No Ensino Médio foram mantidas as competências expressamente associadas nos quadros. Na Educação Infantil são informados os direitos de aprendizagem. AF, AC e EF não foram atribuídos às novas fichas.

## Códigos em revisão

| Código original | Origem | Resultado |
|---|---|---|
| EF13LP03 | 1º ano LP!H12 | Faixa inexistente para Língua Portuguesa na BNCC; não há substituição inequívoca. |
| EM02MA18 | 3º ano MT!I13 | Código inexistente; EF02MA18 é hipótese coerente com medidas de tempo, sem substituição automática. |
| EM08MA18 | 9 ano MT!B9 e B12 | Código inexistente; EF08MA18 é hipótese coerente com geometria, sem substituição automática. |

## Verificações

Validação de cobertura e sincronização entre `data.js`, o grafo para download e os dados embutidos no explorador. Os 471 registros originais foram comparados com a extração original disponível no workspace e permanecem iguais; as 3067 relações originais continuam preservadas entre confirmadas e em revisão. Os 520 novos enunciados e suas páginas correspondem à extração do PDF oficial. A renderização textual das 946 fichas foi exercitada nos três painéis do atlas, no explorador e na exportação Markdown. Essa verificação não equivale a teste visual de navegador nem a homologação dos comentários editoriais pelo MEC.

## Fichas acrescentadas

| Código | Tipo | Página impressa | Fonte |
|---|---|---:|---|
'''.replace('SOURCE_URL', URL)
for item in sorted(additions, key=lambda a: a['id']):
    report_md += f"| {item['id']} | {'BNCC oficial' if item['source_kind']=='official_bncc' else 'Revisão da referência'} | {item['page'] or '—'} | [MEC]({item['url']}) |\n"
(ROOT / 'dados/Complementacao_BNCC.md').write_text(report_md, encoding='utf-8')
print('Completed', len(additions), 'records')
print('Themes:', dict(collections.Counter(a['theme'] for a in additions)))
