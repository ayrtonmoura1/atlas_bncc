/* Expanded graph view: independent from app.js so the current atlas remains intact. */
(() => {
  'use strict';
  const D = window.BNCC_DATA;
  if (!D || !window.d3) return;

  const $ = id => document.getElementById(id);
  const canvas = $('full-graph');
  const ctx = canvas.getContext('2d');
  const nodes = D.nodes.map(n => ({...n}));
  const N = new Map(nodes.map(n => [n.id, n]));
  const rawEdges = (D.edges || []).map(e => ({source:e.source, target:e.target, type:e.type, evidence:e.evidence || []}));
  const edges = rawEdges.map(e => ({...e}));
  const incoming = new Map(nodes.map(n => [n.id, []]));
  const outgoing = new Map(nodes.map(n => [n.id, []]));
  for (const edge of rawEdges) {
    if (incoming.has(edge.target)) incoming.get(edge.target).push(edge);
    if (outgoing.has(edge.source)) outgoing.get(edge.source).push(edge);
  }
  const colors = {LP:'#b29aff', MA:'#ffbf69', MAT:'#ffbf69', CI:'#57d7ad', CNT:'#57d7ad', HI:'#6ec7ff', GE:'#ff8ead', EI:'#c0cbd7', ET:'#c0cbd7', EO:'#c0cbd7', CG:'#c0cbd7'};
  const colorDark = {LP:'#8c70ef', MA:'#e39a3d', MAT:'#e39a3d', CI:'#3bbf91', CNT:'#3bbf91', HI:'#59a7dc', GE:'#e4749d', EI:'#aab5c5', ET:'#aab5c5', EO:'#aab5c5', CG:'#aab5c5'};
  const group = n => n.level === 'Educação Infantil' ? 'EI' : n.component_code;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const uniq = values => [...new Set(values)];
  const sourceRefs = D.metadata?.source_references || {};
  const sourceCode = (sheet, cell) => [...new Set(String(cell || '').split('+').map(part => { const key = `${sheet}!${part.trim()}`, row = part.match(/\d+/)?.[0]; return sourceRefs.cells?.[key] || sourceRefs.rows?.[`${sheet}#${row}`]; }).filter(Boolean))].join(' + ');
  const sourceRef = location => { const value = String(location ?? ''), match = value.match(/^(.+?)!([A-Z]+\d+(?:\+[A-Z]+\d+)*)$/); return match ? sourceCode(match[1], match[2]) || value : value; };
  const sourceText = value => { let output = String(value ?? ''); const sheets = [...new Set(Object.keys(sourceRefs.rows || {}).map(key => key.slice(0, key.lastIndexOf('#'))))].sort((a,b) => b.length-a.length).map(sheet => sheet.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')); if (!sheets.length) return output; return output.replace(new RegExp(`(${sheets.join('|')})!([A-Z]+\\d+(?:\\+[A-Z]+\\d+)?)`, 'g'), (all, sheet, cell) => sourceCode(sheet, cell) || all); };
  const termsFor = value => norm(value).trim().split(/\s+/).filter(Boolean);
  const typeNames = {pre_requisito:'Pré-requisito', relacionada:'Relacionada', relacionada_visao_geral:'Relacionada na visão geral', mencao_comentario:'Menção no comentário'};
  const years = n => n.years?.length ? n.years.map(y => y+'º').join(', ')+' ano' : n.level === 'Educação Infantil' ? 'Educação Infantil' : n.level || 'Etapa não informada';
  const recordLabel = (r,n) => r.source_kind === 'official_bncc' ? `${r.sheet} · p. ${r.source_page}` : r.source_kind === 'source_review' ? r.sheet : `${r.sheet} · ${sourceRefs.rows?.[`${r.sheet}#${r.row}`] || n?.id || 'habilidade'}`;
  const firstRecord = n => n.records?.[0] || {text:n.text || '', theme:'Não informado.', objectives:'Não informado.', competencies:'Não informado.', comment:'Não informado.'};
  const relationIds = (list, id, other) => uniq(list.map(e => e.source === id ? e.target : e.source).filter(Boolean));
  const textField = value => `<div class="field-text">${esc(value || 'Não informado.')}</div>`;

  for (const n of nodes) n.search = norm([n.id,n.text,n.component,n.area,...(n.themes || []),...(n.records || []).map(r => [r.theme,r.objectives,r.comment].join(' '))].join(' '));
  const degrees = new Map(nodes.map(n => [n.id, 0]));
  for (const e of rawEdges) { degrees.set(e.source, (degrees.get(e.source)||0)+1); degrees.set(e.target, (degrees.get(e.target)||0)+1); }
  const simulation = d3.forceSimulation(nodes).randomSource(d3.randomLcg(.42)).force('link', d3.forceLink(edges).id(n => n.id).distance(42).strength(.09)).force('charge', d3.forceManyBody().strength(-42)).force('collide', d3.forceCollide().radius(n => 4 + Math.min(5, Math.sqrt(degrees.get(n.id)||0)) + 3)).force('x', d3.forceX(n => Math.cos(Math.max(0, ['LP','MA','CI','HI','GE','EI'].indexOf(group(n)))*Math.PI/3)*420).strength(.055)).force('y', d3.forceY(n => Math.sin(Math.max(0, ['LP','MA','CI','HI','GE','EI'].indexOf(group(n)))*Math.PI/3)*310).strength(.055)).stop();
  for (let i = 0; i < 150; i++) simulation.tick();

  let width = 700, height = 500, dpr = 1, zoom = {k:1,x:0,y:0};
  let selectedId = null, detailTab = 'skill', query = '', matchSet = new Set(), hover = null, gesture = null;
  const searchInput = $('graph-search');

  function matches() {
    const terms = termsFor(query);
    matchSet = new Set(!terms.length ? [] : nodes.filter(n => terms.every(term => n.search.includes(term))).map(n => n.id));
    $('match-count').textContent = terms.length ? `${matchSet.size} encontrada${matchSet.size === 1 ? '' : 's'}` : `${nodes.length} habilidades`;
    $('canvas-empty').hidden = !(terms.length && !matchSet.size);
    renderSearchResults();
  }
  function renderSearchResults() {
    const el = $('search-results');
    const list = [...matchSet].map(id => N.get(id)).sort((a,b) => a.id.localeCompare(b.id));
    el.classList.toggle('has-results', list.length > 0);
    el.innerHTML = list.slice(0, 28).map(n => `<button class="search-result" data-skill="${esc(n.id)}"><b>${esc(n.id)}</b><span>${esc(n.text || n.component)}</span></button>`).join('') + (list.length > 28 ? `<span class="search-result"><b>+${list.length-28}</b><span>outros resultados</span></span>` : '');
  }
  function fit() {
    if (!nodes.length) return;
    const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
    const xmin = Math.min(...xs)-45, xmax = Math.max(...xs)+45, ymin = Math.min(...ys)-45, ymax = Math.max(...ys)+45;
    const scale = Math.min(1.35, (width-60)/Math.max(160, xmax-xmin), (height-60)/Math.max(160, ymax-ymin));
    zoom = {k:Math.max(.08, scale), x:width/2-(xmin+xmax)/2*scale, y:height/2-(ymin+ymax)/2*scale};
    draw();
  }
  function screen(n) { return {x:n.x*zoom.k+zoom.x, y:n.y*zoom.k+zoom.y}; }
  function radius(n) { return Math.max(3.5, (4+Math.min(5,Math.sqrt(degrees.get(n.id)||0)))*Math.min(zoom.k,1.7)); }
  function focusSet() { const set = new Set(matchSet); if (selectedId) set.add(selectedId); return set; }
  function draw() {
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.fillStyle = '#11182c'; ctx.fillRect(0,0,width,height);
    ctx.fillStyle = '#29324a'; for (let x=18; x<width; x+=25) for (let y=18; y<height; y+=25) { ctx.beginPath(); ctx.arc(x,y,.7,0,Math.PI*2); ctx.fill(); }
    const focused = focusSet(); const filtering = query.trim() || selectedId;
    for (const edge of edges) {
      const a = typeof edge.source === 'string' ? N.get(edge.source) : edge.source;
      const b = typeof edge.target === 'string' ? N.get(edge.target) : edge.target;
      if (!a || !b) continue;
      const active = focused.has(a.id) || focused.has(b.id); const pa = screen(a), pb = screen(b);
      ctx.globalAlpha = filtering ? (active ? .9 : .045) : .2;
      ctx.strokeStyle = edge.type === 'pre_requisito' ? '#adbedf' : edge.type === 'mencao_comentario' ? '#c2aa85' : '#b29aff';
      ctx.lineWidth = active ? 1.8 : 1; ctx.setLineDash(edge.type === 'pre_requisito' ? [] : edge.type === 'mencao_comentario' ? [2,5] : [5,4]);
      ctx.beginPath(); ctx.moveTo(pa.x,pa.y); ctx.lineTo(pb.x,pb.y); ctx.stroke(); ctx.setLineDash([]);
      if (edge.type === 'pre_requisito' && active) { const angle=Math.atan2(pb.y-pa.y,pb.x-pa.x), r=radius(b)+3, tx=pb.x-Math.cos(angle)*r, ty=pb.y-Math.sin(angle)*r; ctx.beginPath(); ctx.moveTo(tx,ty); ctx.lineTo(tx-Math.cos(angle-.48)*7,ty-Math.sin(angle-.48)*7); ctx.lineTo(tx-Math.cos(angle+.48)*7,ty-Math.sin(angle+.48)*7); ctx.closePath(); ctx.fillStyle='#adbedf'; ctx.fill(); }
    }
    for (const n of nodes) {
      const p=screen(n), r=radius(n); if (p.x < -60 || p.y < -60 || p.x > width+60 || p.y > height+60) continue;
      const active=focused.has(n.id), searched=matchSet.has(n.id), selected=n.id===selectedId; ctx.globalAlpha=filtering&&!active?.2:1;
      if (searched || selected) { ctx.beginPath(); ctx.arc(p.x,p.y,r+7,0,Math.PI*2); ctx.fillStyle=selected?'#ffffff30':'#ffffff18'; ctx.fill(); ctx.strokeStyle=selected?'#ffffff':'#e4d9ff'; ctx.lineWidth=selected?2:1.2; ctx.stroke(); }
      ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=colors[group(n)] || '#c0cbd7'; ctx.fill(); ctx.strokeStyle=colorDark[group(n)] || '#8490a6'; ctx.lineWidth=1; ctx.stroke();
      const show = searched || selected || zoom.k > 1.45; if (show) { const label=n.id+(n.focal?' ★':''); ctx.font=(selected?'600 ':'')+'12px "Segoe UI",sans-serif'; ctx.textAlign='center'; ctx.textBaseline='top'; const tw=ctx.measureText(label).width; const ty=p.y+r+7; ctx.fillStyle='#11182cef'; ctx.fillRect(p.x-tw/2-4,ty-2,tw+8,18); ctx.fillStyle=selected?'#fff':'#d2ddef'; ctx.fillText(label,p.x,ty); }
    }
    ctx.globalAlpha=1; $('zoom-label').textContent=Math.round(zoom.k*100)+'%';
  }
  function resize() { const rect=$('canvas-wrap').getBoundingClientRect(); width=Math.max(1,rect.width); height=Math.max(1,rect.height); dpr=Math.min(window.devicePixelRatio||1,2); canvas.width=Math.round(width*dpr); canvas.height=Math.round(height*dpr); fit(); }
  function scale(f,x=width/2,y=height/2) { const k=Math.max(.06,Math.min(5,zoom.k*f)), ratio=k/zoom.k; zoom.x=x-(x-zoom.x)*ratio; zoom.y=y-(y-zoom.y)*ratio; zoom.k=k; draw(); }
  function hit(x,y) { let best=null, distance=Infinity; for (const n of nodes) { const p=screen(n), d=Math.hypot(p.x-x,p.y-y); if (d < Math.max(10,radius(n)+5) && d < distance) { best=n; distance=d; } } return best; }

  function relationCards(ids) { return uniq(ids).map(id => { const n=N.get(id); if (!n) return ''; return `<button class="relation-item" data-skill="${esc(id)}"><b>${esc(id)}<span>${n.focal?'AF ★':n.official_status==='unresolved_reference'?'Em revisão':'Com ficha'}</span></b><p>${esc(n.text || n.component)}</p></button>`; }).join('') || '<p class="small">Não informado na fonte.</p>'; }
  function relationSection(n) {
    const before=uniq((incoming.get(n.id)||[]).map(e => e.source));
    const after=uniq((outgoing.get(n.id)||[]).map(e => e.target));
    const related=relationIds(rawEdges.filter(e => ['relacionada','relacionada_visao_geral'].includes(e.type) && (e.source===n.id || e.target===n.id)),n.id);
    const mentions=relationIds(rawEdges.filter(e => e.type==='mencao_comentario' && (e.source===n.id || e.target===n.id)),n.id);
    return `<div class="detail-section"><h3>O que vem antes <span class="badge">${before.length}</span></h3>${relationCards(before)}</div><div class="detail-section"><h3>O que depende dela <span class="badge">${after.length}</span></h3>${relationCards(after)}</div><div class="detail-section"><h3>Pode ser trabalhado junto <span class="badge">${related.length}</span></h3>${relationCards(related)}</div>${mentions.length?`<div class="detail-section"><h3>Menções em comentários <span class="badge">${mentions.length}</span></h3>${relationCards(mentions)}</div>`:''}`;
  }
  function sourceSection(n, r) {
    const source = r.source_url ? `<div class="source-box"><strong>${r.source_kind==='official_bncc'?'Referência oficial':'Referência em revisão'}</strong><p>${esc(sourceText(r.source_note || ''))}</p><a href="${esc(r.source_url)}" target="_blank" rel="noopener noreferrer">Consultar no MEC${r.source_page?` · p. ${r.source_page}`:''}</a>${r.competency_source_url?`<p><a href="${esc(r.competency_source_url)}" target="_blank" rel="noopener noreferrer">Referencial de competências</a></p>`:''}${r.candidate_code?`<p>Possível correção não confirmada: ${esc(r.candidate_code)}</p>`:''}</div>` : '';
    const evidence=rawEdges.filter(e => e.source===n.id || e.target===n.id).map(e => `<details class="source-detail"><summary>${esc(e.source)} ${e.type==='pre_requisito'?'→':'·'} ${esc(e.target)} · ${esc(typeNames[e.type] || e.type)}</summary>${e.evidence.map(v=>`<p>${esc(sourceRef(v.location || ''))}</p>`).join('')}</details>`).join('');
    return `${source}<p class="footer-note">Fichas e relações originais: BNCC_Foco.xlsx. Fichas novas: BNCC oficial do MEC (2018). Orientações pedagógicas novas são editoriais do atlas.</p><div class="detail-section"><h3>Evidências das relações</h3>${evidence || '<p class="small">Nenhuma relação explícita extraída.</p>'}</div>`;
  }
  function skillSection(n, r) {
    const issue=n.issues?.length ? n.issues.map(i => `<div class="notice"><strong>${esc(i.type)}</strong><p>${esc(sourceText(i.value))}</p></div>`).join('') : '';
    return `${issue}<div class="detail-section"><h3>Campo ou unidade temática</h3><p>${esc(r.theme || 'Não informado.')}</p></div><div class="detail-section"><h3>Objetivos de aprendizagem</h3>${textField(r.objectives)}</div><div class="detail-section"><h3>Competências relacionadas</h3>${textField(r.competencies)}</div><div class="detail-section"><h3>Comentários pedagógicos</h3>${textField(r.comment)}</div><p class="footer-note">${esc(recordLabel(r,n))}${r.source_kind?' · Enunciado oficial separado da orientação editorial.':''}</p>`;
  }
  function header(n) { const r=firstRecord(n); return `<div class="detail-toolbar"><span class="eyebrow">${n.official_status==='unresolved_reference'?'REFERÊNCIA EM REVISÃO':n.level==='Educação Infantil'?'OBJETIVO DE APRENDIZAGEM':'FICHA DA HABILIDADE'}</span><button class="detail-close" data-clear-detail type="button" aria-label="Limpar habilidade">×</button></div><h2 class="detail-code">${esc(n.id)}</h2><div class="badges"><span class="badge">${esc(n.component)}</span><span class="badge">${esc(years(n))}</span>${(n.own_classifications||[]).map(c=>`<span class="badge af">${esc(c)}</span>`).join('')}</div><p class="detail-description">${esc(r.text || n.text || 'Enunciado não informado.')}</p>`; }
  function renderSide() {
    const el=$('side-detail'); if (!selectedId) { el.innerHTML='<div class="empty-detail"><div class="empty-icon">◎</div><span class="eyebrow">SELECIONE UM PONTO</span><h2>Leia a ficha ao lado</h2><p>A busca destaca os resultados no mapa. Clique em uma habilidade para abrir suas conexões, comentários e fonte.</p></div>'; return; }
    const n=N.get(selectedId), r=firstRecord(n); const tabs=[['skill','Habilidade'],['connections','Conexões'],['source','Fonte']];
    const content=detailTab==='skill'?skillSection(n,r):detailTab==='connections'?relationSection(n):sourceSection(n,r);
    el.innerHTML=`${header(n)}<div class="detail-tabs">${tabs.map(([id,label])=>`<button type="button" class="${detailTab===id?'active':''}" data-tab="${id}">${label}</button>`).join('')}</div><section>${content}</section><button class="primary-action" data-open-modal type="button">Abrir ficha completa</button>`;
  }
  function renderModal() {
    const n=N.get(selectedId); if (!n) return; const r=firstRecord(n); $('modal-title').textContent=n.id; $('modal-content').innerHTML=`<p class="detail-description">${esc(r.text || n.text || '')}</p><div class="modal-block"><h3>Habilidade e orientação</h3>${skillSection(n,r)}</div><div class="modal-block"><h3>Conexões</h3>${relationSection(n)}</div><div class="modal-block"><h3>Fonte</h3>${sourceSection(n,r)}</div>`;
  }
  function selectNode(id, open=true) { if (!N.has(id)) return; selectedId=id; detailTab='skill'; renderSide(); draw(); if (open) { renderModal(); if (!$('skill-modal').open) $('skill-modal').showModal(); } }

  searchInput.addEventListener('input', () => { query=searchInput.value; matches(); draw(); });
  $('clear-search').addEventListener('click', () => { searchInput.value=''; query=''; matches(); draw(); searchInput.focus(); });
  $('fit').addEventListener('click', fit); $('zoom-in').addEventListener('click', () => scale(1.3)); $('zoom-out').addEventListener('click', () => scale(1/1.3));
  $('fullscreen').addEventListener('click', async () => { try { if (!document.fullscreenElement) await document.documentElement.requestFullscreen(); else await document.exitFullscreen(); } catch { $('toast').textContent='A tela cheia não está disponível neste navegador.'; $('toast').hidden=false; setTimeout(()=>$('toast').hidden=true,2600); } });
  $('close-modal').addEventListener('click', () => $('skill-modal').close()); $('skill-modal').addEventListener('click', e => { const rect=$('skill-modal').getBoundingClientRect(); if (e.target === $('skill-modal') && (e.clientX<rect.left || e.clientX>rect.right || e.clientY<rect.top || e.clientY>rect.bottom)) $('skill-modal').close(); });
  document.addEventListener('click', e => { const skill=e.target.closest('[data-skill]'); if (skill) { e.preventDefault(); selectNode(skill.dataset.skill, true); return; } const tab=e.target.closest('[data-tab]'); if (tab && selectedId) { detailTab=tab.dataset.tab; renderSide(); } const clear=e.target.closest('[data-clear-detail]'); if (clear) { selectedId=null; renderSide(); draw(); } const open=e.target.closest('[data-open-modal]'); if (open && selectedId) { renderModal(); if (!$('skill-modal').open) $('skill-modal').showModal(); } });
  let pointers=new Map();
  canvas.addEventListener('pointerdown', e => { const r=canvas.getBoundingClientRect(), p={x:e.clientX-r.left,y:e.clientY-r.top}; pointers.set(e.pointerId,p); canvas.setPointerCapture(e.pointerId); gesture={start:p,last:p,moved:false}; canvas.classList.add('dragging'); });
  canvas.addEventListener('pointermove', e => { const r=canvas.getBoundingClientRect(), p={x:e.clientX-r.left,y:e.clientY-r.top}; if (pointers.has(e.pointerId)) { pointers.set(e.pointerId,p); if (gesture) { const dx=p.x-gesture.last.x,dy=p.y-gesture.last.y; if (Math.hypot(p.x-gesture.start.x,p.y-gesture.start.y)>4) gesture.moved=true; if (gesture.moved) { zoom.x+=dx; zoom.y+=dy; } gesture.last=p; draw(); return; } const n=hit(p.x,p.y); if (n!==hover) { hover=n; draw(); } } });
  canvas.addEventListener('pointerup', e => { pointers.delete(e.pointerId); if (!pointers.size) { canvas.classList.remove('dragging'); const g=gesture; gesture=null; if (g && !g.moved) { const r=canvas.getBoundingClientRect(), n=hit(e.clientX-r.left,e.clientY-r.top); if (n) selectNode(n.id,true); } } });
  canvas.addEventListener('pointercancel', e => { pointers.delete(e.pointerId); gesture=null; canvas.classList.remove('dragging'); });
  canvas.addEventListener('pointerleave', () => { if (!pointers.size) { hover=null; $('canvas-tip').hidden=true; draw(); } });
  canvas.addEventListener('wheel', e => { e.preventDefault(); const r=canvas.getBoundingClientRect(); scale(Math.exp(-e.deltaY*.0015), e.clientX-r.left, e.clientY-r.top); }, {passive:false});
  canvas.addEventListener('mousemove', e => { if (pointers.size) return; const r=canvas.getBoundingClientRect(), p={x:e.clientX-r.left,y:e.clientY-r.top}, n=hit(p.x,p.y), tip=$('canvas-tip'); tip.hidden=!n; canvas.style.cursor=n?'pointer':'grab'; if (n) { tip.innerHTML=`<strong>${esc(n.id)}${n.focal?' ★':''}</strong><p>${esc(n.component)} · ${esc(years(n))}</p><p>${esc((n.text || '').slice(0,170))}${(n.text || '').length>170?'…':''}</p>`; tip.style.left=Math.max(8,Math.min(width-285,p.x+16))+'px'; tip.style.top=Math.max(8,Math.min(height-130,p.y+16))+'px'; } });
  window.addEventListener('resize', resize); if (window.ResizeObserver) new ResizeObserver(resize).observe($('canvas-wrap'));
  $('edge-count').textContent=`· ${rawEdges.length} relações`;
  matches(); renderSide(); resize();
})();
