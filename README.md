# Atlas BNCC — habilidades em conexão

Site estático, pronto para publicação. Não há etapa de build: os arquivos já são
o artefato final e funcionam abertos por HTTP(S) a partir da raiz desta pasta.

## Estrutura

```
atlas_bncc/
├── index.html                     # página principal (Atlas BNCC)
├── explorador.html                # explorador autônomo (dados embutidos)
├── app.js                         # lógica do atlas
├── data.js                        # dados embutidos (window.BNCC_DATA)
├── styles.css                     # estilos
├── .openai/hosting.json           # diretório estático = raiz (".")
├── vendor/
│   ├── d3.min.js
│   ├── lucide.min.js
│   ├── LICENSE-d3.txt
│   └── LICENSE-lucide.txt
└── dados/                         # arquivos para download e transparência
    ├── BNCC_Analise_e_Modelo.md
    ├── BNCC_Grafo.json
    ├── BNCC_Relacoes.csv
    ├── Auditoria.md
    └── auditoria.json
```

## Publicação

Publique **esta pasta** como raiz do site (não use uma subpasta `dist`, ela não existe mais).
Todos os caminhos internos são relativos (`./`), então o site funciona tanto na raiz do
domínio quanto em um subdiretório (por exemplo, `usuario.github.io/atlas-bncc/`).

| Plataforma | Configuração |
|---|---|
| Azure Static Web Apps / OpenAI hosting | já definido em `.openai/hosting.json` (`static.directory = "."`) |
| GitHub Pages | publique o conteúdo desta pasta na branch/raiz do site |
| Netlify / Cloudflare Pages | build command: *(vazio)* · publish directory: `.` |
| Vercel | framework: *Other* · build command: *(vazio)* · output directory: `.` |
| Servidor próprio (nginx/Apache/IIS) | aponte o `document root` para esta pasta |

## Verificação local

Qualquer servidor estático serve. Exemplos:

```powershell
# Python
python -m http.server 4180 --directory atlas_bncc

# Node (npx)
npx --yes serve atlas_bncc
```

Depois abra `http://localhost:4180/`.

Na ficha selecionada, o botão de download gera um PDF diagramado com enunciado,
contexto, objetivos, competências, comentários, conexões e fontes. O PDF é criado
no navegador e recebe o nome `Atlas-BNCC-CODIGO.pdf`.

> Abrir `index.html` diretamente pelo protocolo `file://` carrega o mapa, mas o botão
> "Copiar link desta habilidade" avisa que o link compartilhável só funciona após publicar.
> Isso é esperado, não é erro.

## Observações técnicas

- Sem dependências externas em tempo de execução: D3 e Lucide são locais; o favicon é SVG embutido.
- Sem requisições `fetch` de dados: tudo vem de `data.js`; os arquivos em `dados/` são apenas downloads.
- Sem cookies, contas, rastreamento ou CDNs.
- Navegação por estado via `#hash`, portanto não é necessário rewrite de servidor.
- `dados/BNCC_Relacoes.csv` tem BOM UTF-8 intencional, para abrir corretamente no Excel.

## Fonte

Base: `BNCC_Foco.xlsx` (59 abas, 946 códigos). Os Mapas de Foco têm idealização do
Instituto Reúna e realização do Instituto Reúna e Fundação Itaú Social. Este site é uma
visualização independente.

## Complementação das fichas — 18/09/2026

Todas as 943 habilidades válidas presentes na base têm ficha: 423 preservam os
registros originais e 520 foram completadas com o enunciado da BNCC oficial do MEC,
campo/unidade, objetivos, referencial de competências, orientação pedagógica e fonte.
Cada nova ficha indica a página impressa e oferece um link para a página do PDF.
Os comentários novos são editoriais e não são atribuídos ao MEC ou ao Instituto Reúna.

Os códigos `EF13LP03`, `EM02MA18` e `EM08MA18` não constam na BNCC oficial. Possuem
ficha de revisão com evidência da origem; não receberam enunciados inventados.
As quatro relações que os envolvem permanecem em `unconfirmed_edges` e no CSV,
identificadas como em revisão. O grafo utiliza 3063 relações, sendo 587 pré-requisitos.

Relatório: [Complementacao_BNCC.md](dados/Complementacao_BNCC.md).
Índice das novas fontes: [complementacao_bncc.json](dados/complementacao_bncc.json).
A complementação cobre os códigos existentes no atlas, não todos os componentes da BNCC.

Verificação de cobertura, sincronização, referências e renderização textual das fichas:

```powershell
python scripts/validate_bncc.py
node scripts/validate_cards.cjs
node --check app.js
```

Para reproduzir a extração, obtenha o PDF no endereço oficial registrado no relatório,
salve-o em `tmp/bncc/oficial.pdf` e execute `scripts/extract_bncc.py` seguido de
`scripts/complete_bncc.py` (Python e PyMuPDF). A complementação é idempotente e
preserva os registros originais. `tmp/` contém apenas materiais de conferência.
