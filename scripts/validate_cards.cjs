/* Exercise card rendering and Markdown exports without browser automation. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
function environment() {
  const elements = new Map();
  const el = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', textContent: '', value: id === 'depth' ? '1' : '', checked: false, style: {}, options: [],
      add(option) { this.options.push(option); }, addEventListener() {}, setAttribute() {},
      querySelectorAll() { return []; }, getContext() { return {}; }, click() {}, focus() {},
    });
    return elements.get(id);
  };
  const captures = [];
  const context = vm.createContext({
    document: {getElementById: el, querySelectorAll: () => [], createElement: () => el('download'), addEventListener() {}},
    window: {d3: {}, lucide: null},
    Option: function(text, value) { this.text = text; this.value = value; },
    URL: {createObjectURL: blob => { captures.push(blob.text); return 'blob:test'; }, revokeObjectURL() {}},
    Blob: class { constructor(parts) { this.text = parts.join(''); } },
    setTimeout() {}, clearTimeout() {}, console,
  });
  return {context, el, captures};
}
const atlas = environment();
vm.runInContext(fs.readFileSync(path.join(root, 'data.js'), 'utf8'), atlas.context);
let app = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
app = app.slice(0, app.indexOf("canvas.addEventListener('pointerdown'")) + `
window.testCard=(id,tab)=>{state.id=id;state.tab=tab;state.record=0;renderDetail();};
window.testDownload=id=>{state.id=id;downloadNote();};
})();`;
vm.runInContext(app, atlas.context);
const nodes = atlas.context.window.BNCC_DATA.nodes;
for (const n of nodes) {
  for (const tab of ['skill', 'connections', 'source']) {
    atlas.context.window.testCard(n.id, tab);
    const html = atlas.el('detail-content').innerHTML;
    assert(html.includes(n.id), n.id);
    assert(!html.includes('linha null'), n.id);
    assert(!html.includes('undefined'), n.id);
    if (n.records[0].source_kind === 'official_bncc') {
      assert(html.includes(n.records[0].source_url), n.id);
      assert(html.includes('Orientação pedagógica elaborada'), n.id);
    }
  }
  atlas.context.window.testDownload(n.id);
  const md = atlas.captures.at(-1);
  assert(md.startsWith('# ' + n.id), n.id);
  assert(md.includes('### Campo ou unidade temática'), n.id);
  assert(!md.includes('linha null'), n.id);
  if (n.records[0].source_url) assert(md.includes(n.records[0].source_url), n.id);
}
const standalone = environment();
let html = fs.readFileSync(path.join(root, 'explorador.html'), 'utf8');
let script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script); // Also syntax-check the complete shipped script.
script += '\nglobalThis.testCard=id=>{selected=id;render();};';
vm.runInContext(script, standalone.context);
for (const n of nodes) {
  standalone.context.testCard(n.id);
  assert.equal(standalone.el('detailTitle').textContent, n.id);
  const card = standalone.el('records').innerHTML;
  assert(!card.includes('linha null'), n.id);
  assert(!card.includes('undefined'), n.id);
  if (n.records[0].source_url) assert(card.includes(n.records[0].source_url), n.id);
}
console.log(`Passed: ${nodes.length} Atlas cards × 3 tabs, ${nodes.length} Markdown exports, ${nodes.length} standalone cards.`);
