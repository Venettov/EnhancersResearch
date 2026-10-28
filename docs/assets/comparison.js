/* Explore recorded predictions; never query the authors' service. */
(() => {
  'use strict';
  const app = document.querySelector('[data-comparison-explorer]');
  if (!app) return;
  const es = document.documentElement.lang === 'es', tr = (en, spanish) => es ? spanish : en;
  const url = new URL('../data/predictor_reference_200.json', document.currentScript.src);
  const keys = ['strong','weak','non-enhancer'];
  const names = {strong:tr('Strong','Fuerte'),weak:tr('Weak','Débil'),'non-enhancer':tr('Non-enhancer','No potenciador')};
  const matrix = app.querySelector('[data-agreement-matrix]');
  const panel = app.querySelector('[data-explorer-panel]');
  const status = app.querySelector('[data-explorer-status]');
  const body = app.querySelector('[data-explorer-rows]');
  let records = [], selected = 'different';
  const buttons = [];
  const selectionName = () => selected === 'all' ? tr('All comparisons','Todas las comparaciones') : selected === 'different' ? tr('Disagreements','Diferencias') :
    tr('Authors: ','Autores: ') + names[selected.split('/')[0]] + ' · ' + tr('Ours: ','Nuestro: ') + names[selected.split('/')[1]];
  function render() {
    const rows = records.filter(row => selected === 'all' || (selected === 'different' ? row.server_class !== row.local_class : `${row.server_class}/${row.local_class}` === selected));
    buttons.forEach(button => button.setAttribute('aria-pressed',String(button.dataset.selection === selected)));
    status.textContent = selectionName() + ' · ' + tr(`${rows.length} of ${records.length} sequences.`,`${rows.length} de ${records.length} secuencias.`);
    const fragment = document.createDocumentFragment();
    rows.forEach(row => {
      const line = document.createElement('tr');
      const values = [row.probe_id,names[row.server_class],names[row.local_class],row.server_class === row.local_class ? tr('Match','Coincide') : tr('Different','Diferente'),Number(row.local_enhancer_score).toFixed(8),row.local_strength_score === '' || row.local_strength_score === null ? '—' : Number(row.local_strength_score).toFixed(8)];
      values.forEach((value,i) => { const cell = document.createElement(i===0?'th':'td'); if(i===0) cell.scope='row'; cell.textContent=value; line.append(cell); });
      fragment.append(line);
    });
    body.replaceChildren(fragment);
    app.querySelector('[data-explorer-empty]').hidden = rows.length !== 0;
  }
  function register(button, selection) {
    button.dataset.selection = selection; button.setAttribute('aria-controls','comparison-sequences');
    button.addEventListener('click',() => { selected=selection; render(); }); buttons.push(button);
  }
  fetch(url).then(response => { if(!response.ok) throw new Error('unavailable'); return response.json(); }).then(data => {
    if (!Array.isArray(data) || data.length !== 200 || data.some(row => !keys.includes(row.server_class) || !keys.includes(row.local_class) || !Number.isFinite(Number(row.local_enhancer_score)) || (row.local_strength_score && !Number.isFinite(Number(row.local_strength_score))))) throw new Error('invalid');
    records = data;
    const cells = [...matrix.querySelectorAll('tbody td')];
    if(cells.length !== 9) throw new Error('matrix');
    // Refuse enhancement if the saved evidence and the readable static table disagree.
    const counts = cells.map((cell,i) => records.filter(row => row.server_class === keys[Math.floor(i/3)] && row.local_class === keys[i%3]).length);
    if(cells.some((cell,i) => Number(cell.textContent.trim()) !== counts[i])) throw new Error('counts');
    cells.forEach((cell,i) => {
      const author = keys[Math.floor(i/3)], ours = keys[i%3], count = counts[i];
      const button = document.createElement('button'); button.type='button'; button.textContent=String(count);
      button.className = 'agreement-cell ' + (author === ours ? 'agreement-match':'agreement-different');
      button.style.setProperty('--intensity',String(.12 + .7*count/Math.max(...counts)));
      button.setAttribute('aria-label',tr(`Authors: ${names[author]}; ours: ${names[ours]}; ${count} sequences.`, `Autores: ${names[author]}; nuestro: ${names[ours]}; ${count} secuencias.`));
      register(button,`${author}/${ours}`); cell.replaceChildren(button);
    });
    register(app.querySelector('[data-explorer-all]'),'all');
    register(app.querySelector('[data-explorer-different]'),'different');
    panel.hidden=false; app.querySelector('[data-explorer-help]').hidden=false; render();
  }).catch(() => {
    status.textContent = tr('The interactive rows could not load. The recorded comparison table and CSV downloads remain available below.',
      'No se pudieron cargar las filas interactivas. La tabla guardada y las descargas CSV siguen disponibles debajo.');
  });
})();
