const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// Minimal DOM adapter: production event handlers, filtering and rendering run unmodified.
class Element {
  constructor(tag = 'div', attrs = {}, text = '') {
    this.tagName = tag; this.attrs = {...attrs}; this.children = []; this.parentNode = null;
    this.text = text; this.value = ''; this.hidden = false; this.events = {}; this.style = {};
    this.dataset = new Proxy({}, {get: (_, k) => this.getAttribute('data-' + k.replace(/[A-Z]/g, x => '-' + x.toLowerCase())),
      set: (_, k, v) => {this.setAttribute('data-' + k.replace(/[A-Z]/g, x => '-' + x.toLowerCase()), v); return true;}});
    this.classList = {contains: c => this.className.split(/\s+/).includes(c),
      toggle: (c, on) => {let s = new Set(this.className.split(/\s+/).filter(Boolean));
        if (on ?? !s.has(c)) s.add(c); else s.delete(c); this.className = [...s].join(' ');},
      add: c => this.classList.toggle(c, true), remove: c => this.classList.toggle(c, false)};
  }
  get className() {return this.attrs.class || '';}
  set className(v) {this.attrs.class = v;}
  get href() {return this.attrs.href || '';}
  set href(v) {this.attrs.href = v;}
  get dateTime() {return this.attrs.datetime || '';}
  get textContent() {return this.text + this.children.map(c => c.textContent).join('');}
  set textContent(v) {this.text = String(v); this.children = [];}
  getAttribute(k) {return this.attrs[k] ?? null;}
  hasAttribute(k) {return k in this.attrs;}
  setAttribute(k, v) {this.attrs[k] = String(v);}
  removeAttribute(k) {delete this.attrs[k];}
  toggleAttribute(k, yes) {if (yes ?? !(k in this.attrs)) this.setAttribute(k, ''); else this.removeAttribute(k);}
  appendChild(c) {if (c.parentNode) c.parentNode.children.splice(c.parentNode.children.indexOf(c), 1);
    this.children.push(c); c.parentNode = this; return c;}
  replaceChildren(...children) {this.children = []; this.text = ''; children.forEach(c => this.appendChild(c));}
  addEventListener(type, fn) {(this.events[type] ||= []).push(fn);}
  fire(type) {(this.events[type] || []).forEach(fn => fn({target:this}));}
  focus() {}
  scrollIntoView() {}
  matches(selector) {
    return selector.split(',').some(branch => {
      let tokens = branch.trim().split(/\s+/), node = this;
      if (!simple(node, tokens.pop())) return false;
      while (tokens.length) {let token = tokens.pop(); node = node.parentNode;
        while (node && !simple(node, token)) node = node.parentNode;
        if (!node) return false;
      }
      return true;
    });
  }
  closest(s) {let n = this; while (n && !n.matches(s)) n = n.parentNode; return n;}
  querySelectorAll(s) {return this.children.flatMap(c => [...(c.matches(s) ? [c] : []), ...c.querySelectorAll(s)]);}
  querySelector(s) {return this.querySelectorAll(s)[0] || null;}
}
function simple(node, s) {
  const tag = s.match(/^[\w-]+/); if (tag && node.tagName !== tag[0]) return false;
  for (const m of s.matchAll(/\.([\w-]+)/g)) if (!node.classList.contains(m[1])) return false;
  for (const m of s.matchAll(/\[([\w-]+)(?:=["']?([^\]"']+)["']?)?\]/g)) {
    if (node.getAttribute(m[1]) === null || (m[2] !== undefined && node.getAttribute(m[1]) !== m[2])) return false;
  }
  return !s.includes('>');
}
function fixture({contextPosition, contextSources=['24horas'], contextOnly=false, recent=false} = {}) {
  let d = new Element('document'); d.body = d;
  d.getElementById = id => d.querySelectorAll('[id]').find(x => x.attrs.id === id) || null;
  d.createElement = tag => new Element(tag); d.createTextNode = text => new Element('#text', {}, text);
  const add = (tag, attrs, text, parent=d) => parent.appendChild(new Element(tag, attrs, text));
  const ids = ['search-toggle','search-panel','search-input','search-status','search-results','search-category',
    'search-source','search-date','source-preference','category-preference','source-sort','library-panel','library-toggle','saved-stories'];
  ids.forEach(id => add('div', {id}));
  const main = add('main', {id:'contenido'});
  const addContext = () => {
    const context = add('section', {class:'context'}, '', main);
    add('a', {'data-cat':'Chile','data-key':'chile','data-sources':JSON.stringify(contextSources),
      href:'https://example.com/25'}, 'Noticia común 25', context);
    if (contextOnly) add('a', {'data-cat':'Chile','data-key':'chile','data-sources':'["Contextual"]',
      href:'https://example.com/context-only'}, 'Sólo contexto', context);
  };
  if (contextPosition === 'before') addContext();
  const section = add('section', {class:'section'}, '', main);
  const grid = add('div', {class:'section-grid', id:'noticias-grupo'}, '', section);
  const list = new Element('ul', {class:'compact-list'});
  for (let i=0; i<26; i++) {
    const card = i===0 ? add('article', {class:'feature'}, '', grid) : add('li', i>5 ? {'data-extra':''} : {}, '', list);
    const h = add('h3', {}, '', card), names = i === 25 ? ['24horas','Teletrece','Oculto'] : [i>8 ? 'Teletrece' : 'Otro'];
    add('a', {'data-cat':'Chile','data-key':'chile','data-sources':JSON.stringify(names), href:'https://example.com/'+i}, 'Noticia común '+i, h);
    const meta = add('p', {class:'meta'}, '', card);
    add('span', {class:'source-name'}, i===25 ? '24horas, Teletrece' : names[0], meta);
    add('time', {datetime:new Date(recent ? Date.now()-3600000+i : Date.UTC(2026,9,22,0,i)).toISOString()}, '', meta);
  }
  grid.appendChild(list);
  const more = add('button', {'data-show-more':'','aria-controls':'noticias-grupo','data-step':'6'}, '', section);
  if (contextPosition === 'after') addContext();
  const storage = new Map();
  const context = {document:d, window:{addEventListener(){}}, localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
    URL, Date, console, setTimeout(){},setInterval(){}};
  const html = fs.readFileSync('template.html','utf8');
  const script = [...html.matchAll(/<script>\s*([\s\S]*?)<\/script>/g)].at(-1)[1];
  vm.runInNewContext(script, context);
  const change = (id, value, event='change') => {let el=d.getElementById(id);el.value=value;el.fire(event);};
  const visible = () => grid.querySelectorAll('.feature,.compact-list li').filter(x => x.getAttribute('data-source-hidden')===null && x.getAttribute('data-extra')===null);
  return {d, grid, list, more, change, visible};
}

test('search renders every announced result beyond twenty', () => {
  const f=fixture(); f.change('search-input', 'comun', 'input');
  assert.equal(f.d.getElementById('search-status').textContent, '26 resultados');
  assert.equal(f.d.getElementById('search-results').children.length, 26);
});
test('context-first duplicates retain card metadata and all twenty-six recent search results', () => {
  const f=fixture({contextPosition:'before', recent:true});
  f.change('search-input','comun','input');
  assert.equal(f.d.getElementById('search-results').children.length,26);
  f.change('search-date','24');
  const results=f.d.getElementById('search-results').children;
  assert.equal(f.d.getElementById('search-status').textContent,'26 resultados');
  assert.equal(results.length,26);
  const duplicate=results.find(li=>li.querySelector('a').href==='https://example.com/25');
  assert.equal(duplicate.querySelector('.search-result-meta').textContent,'24horas, Teletrece');
  f.change('search-source','Oculto');
  assert.equal(f.d.getElementById('search-results').children.length,1);
  assert.equal(f.d.getElementById('search-results').children[0].querySelector('a').href,'https://example.com/25');
});
test('duplicate links preserve complete sources in either document order', () => {
  for (const contextPosition of ['before','after']) {
    const f=fixture({contextPosition, contextSources:['Contextual'], recent:true});
    for (const source of ['Contextual','24horas','Teletrece','Oculto']) {
      assert.ok(f.d.getElementById('search-source').children.some(x=>x.value===source));
      f.change('search-input','comun 25','input');
      f.change('search-source',source);
      f.change('search-date','24');
      assert.equal(f.d.getElementById('search-results').children.length,1,contextPosition+': '+source);
    }
  }
});
test('stories present only in context remain searchable without invented metadata', () => {
  const f=fixture({contextPosition:'before', contextOnly:true});
  f.change('search-input','solo contexto','input');
  let results=f.d.getElementById('search-results').children;
  assert.equal(results.length,1);
  assert.equal(results[0].querySelector('a').href,'https://example.com/context-only');
  assert.equal(results[0].querySelector('.search-result-meta').textContent,'');
  f.change('search-source','Contextual');
  assert.equal(f.d.getElementById('search-results').children.length,1);
  f.change('search-date','24');
  assert.equal(f.d.getElementById('search-results').children.length,0);
});
test('source selectors use each complete source, including names absent from the abbreviated label', () => {
  const f=fixture();
  assert.ok(f.d.getElementById('search-source').children.some(x => x.value==='Oculto'));
  f.change('search-source','Oculto');
  assert.equal(f.d.getElementById('search-results').children.length,1);
  f.change('source-preference','Teletrece');
  assert.equal(f.visible().length,6);
  assert.ok(f.visible().every(c => JSON.parse(c.querySelector('a').getAttribute('data-sources')).includes('Teletrece')));
});
test('filtered stories reveal six at a time and resetting restores the first six', () => {
  const f=fixture(); assert.equal(f.visible().length,6);
  f.change('source-preference','Teletrece'); assert.equal(f.visible().length,6);
  assert.equal(f.more.hidden,false); f.more.fire('click'); assert.equal(f.visible().length,12);
  f.more.fire('click'); assert.equal(f.visible().length,17); assert.equal(f.more.hidden,true);
  f.change('source-preference',''); assert.equal(f.visible().length,6); assert.equal(f.more.hidden,false);
});
test('recent sorting exposes new first stories and editorial sorting restores original order', () => {
  const f=fixture(); f.change('source-sort','recent');
  assert.equal(f.list.children[0].querySelector('a').textContent,'Noticia común 25');
  assert.equal(f.list.children[0].getAttribute('data-extra'),null);
  assert.equal(f.visible().length,6);
  f.change('source-sort','relevance');
  assert.equal(f.list.children[0].querySelector('a').textContent,'Noticia común 1');
  assert.equal(f.visible().length,6);
});
