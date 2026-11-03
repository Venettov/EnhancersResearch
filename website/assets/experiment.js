/* Previously exposed examples only: display saved scores and published means. */
(() => {
  'use strict';
  const app = document.querySelector('[data-experiment]');
  if (!app) return;
  const es = document.documentElement.lang === 'es', tr = (en, spanish) => es ? spanish : en;
  const url = new URL('../data/lentimpra_demo_200.json', document.currentScript.src);
  const q = selector => app.querySelector(selector);
  const cellSelect = q('#experiment-cell'), probeSelect = q('#experiment-probe');
  const search = q('#experiment-search'), coverage = q('#experiment-coverage');
  const plot = q('[data-experiment-plot]'), status = q('[data-experiment-status]');
  const cells = ['HepG2', 'K562', 'WTC11'];
  const number = (value, places = 3) => Number.isFinite(value) ? value.toFixed(places) : '—';
  const category = row => row.category === 'promoter' ? tr('Promoter', 'Promotor') : tr('Candidate enhancer, HepG2', 'Potenciador candidato, HepG2');
  const predicted = row => ({strong:tr('Strong enhancer','Potenciador fuerte'),weak:tr('Weak enhancer','Potenciador débil'),
    'non-enhancer':tr('Non-enhancer','No potenciador')})[row.predicted_class];
  const reason = row => row.eligible ? tr('Included in plots','Incluida en las gráficas') : row.s11_summary_row === null ? tr('No published summary','Sin resumen publicado') : tr('Below coverage rule','Cobertura insuficiente');
  let records = [], eligible = [], selected, xDomain, yDomain;
  function element(tag, text) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; return el; }
  function svgElement(tag, attrs, text) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function drawPlot() {
    const width = Math.max(240, plot.clientWidth), height = 370;
    const left = 58, right = width - 20, top = 20, bottom = height - 62;
    const x = value => left + (value - xDomain[0]) / (xDomain[1] - xDomain[0]) * (right - left);
    const y = value => bottom - (value - yDomain[0]) / (yDomain[1] - yDomain[0]) * (bottom - top);
    const cell = cellSelect.value;
    const svg = svgElement('svg', {viewBox:`0 0 ${width} ${height}`, role:'img', 'aria-label':tr(
      `${cell}: saved Layer I score versus published mean log2 RNA/DNA for 185 eligible sequences. Values are also available in the table.`,
      `${cell}: puntuación guardada de la capa I frente a la media publicada de log2 ARN/ADN para 185 secuencias elegibles. Los valores también están en la tabla.`)});
    for (let yv = yDomain[0]; yv <= yDomain[1]; yv++) {
      svg.append(svgElement('line',{x1:left,x2:right,y1:y(yv),y2:y(yv),stroke:'#d6e0dc'}));
      svg.append(svgElement('text',{x:left-9,y:y(yv)+4,'text-anchor':'end'},String(yv)));
    }
    for (let xv = xDomain[0]; xv <= xDomain[1]; xv++)
      svg.append(svgElement('text',{x:x(xv),y:bottom+22,'text-anchor':'middle'},String(xv)));
    svg.append(svgElement('line',{x1:left,x2:left,y1:top,y2:bottom,stroke:'#718d92'}));
    svg.append(svgElement('line',{x1:left,x2:right,y1:bottom,y2:bottom,stroke:'#718d92'}));
    svg.append(svgElement('text',{x:(left+right)/2,y:height-12,'text-anchor':'middle'},tr('Layer I decision score','Puntuación de la capa I')));
    svg.append(svgElement('text',{transform:`translate(15 ${(top+bottom)/2}) rotate(-90)`,'text-anchor':'middle'},`${cell} · log2(${tr('RNA/DNA','ARN/ADN')})`));
    // Draw the selected dot last, so it remains visible when points overlap.
    for (const row of [...eligible.filter(r => r !== selected), ...eligible.filter(r => r === selected)]) {
      const value = row.activity[cell].mean_log2_rna_dna;
      const dot = svgElement('circle',{cx:x(row.layer1_score),cy:y(value),r:row===selected?6:3.5,
        class:'plot-point'+(row===selected?' is-selected':''),'data-probe':row.probe_id});
      dot.append(svgElement('title',{},`${row.probe_id} · ${tr('score','puntuación')} ${number(row.layer1_score,4)} · ${cell} ${number(value)}`));
      dot.addEventListener('click',()=>select(row.probe_id)); svg.append(dot);
    }
    plot.replaceChildren(svg);
  }
  function drawDetails() {
    const row = selected;
    q('[data-probe-title]').textContent = row.probe_id;
    q('[data-construct]').textContent = row.construct;
    q('[data-sequence-category]').textContent = category(row);
    q('[data-layer1]').textContent = number(row.layer1_score,4);
    q('[data-prediction]').textContent = tr('Historical model label: ','Etiqueta histórica del modelo: ') + predicted(row);
    q('[data-coverage]').textContent = reason(row) + (row.eligible ? tr(' · same score in all cells.',' · la misma puntuación en todas las células.') : tr(' · retained here for transparency.',' · se conserva aquí para mostrar todos los registros.'));
    const body = q('[data-sequence-activity]'), reps = q('[data-replicates]');
    body.replaceChildren(); reps.replaceChildren();
    for (const cell of cells) {
      const a = row.activity[cell], line = element('tr'), label = element('th',cell); label.scope='row';
      line.append(label,element('td',number(a.mean_log2_rna_dna)),element('td',`${a.replicates.filter(r=>r.barcodes>=10).length} / ${a.replicates.length}`)); body.append(line);
      const p = element('p'); p.append(element('strong',cell+': '));
      p.append(document.createTextNode(a.replicates.length ? a.replicates.map(r=>tr(
        `replicate ${r.replicate}: ${number(r.log2_rna_dna)} (${r.barcodes} barcodes)`,
        `réplica ${r.replicate}: ${number(r.log2_rna_dna)} (${r.barcodes} códigos de barras)`)).join('; ') : tr('No reported replicates.','Sin réplicas publicadas.'))); reps.append(p);
    }
    q('[data-sequence-hash]').textContent = row.sequence_sha256;
    q('[data-sequence-source]').textContent = tr(`S10 design row ${row.s10_row}; S11 shared summary row ${row.s11_summary_row ?? '—'}.`,
      `Fila ${row.s10_row} del diseño S10; fila ${row.s11_summary_row ?? '—'} del resumen compartido S11.`);
    q('[data-predict-sequence]').href = 'predictor.html?example=lentimpra&probe=' + encodeURIComponent(row.probe_id);
    status.textContent = tr(`Inspecting ${row.probe_id}. Plot: ${cellSelect.value}, 185 eligible sequences.`,
      `Inspeccionando ${row.probe_id}. Gráfica: ${cellSelect.value}, 185 secuencias elegibles.`);
  }
  function drawTable() {
    const term = search.value.trim().toLocaleLowerCase();
    const rows = records.filter(r=>(r.probe_id+' '+r.construct).toLocaleLowerCase().includes(term) &&
      (coverage.value==='all' || r.eligible === (coverage.value==='eligible')));
    const fragment = document.createDocumentFragment();
    for (const row of rows) {
      const line = element('tr'); if(row===selected) line.className='is-selected';
      const label = element('th'); label.scope='row';
      const button = element('button',row.probe_id); button.type='button';
      button.addEventListener('click',()=>{select(row.probe_id);q('[data-probe-title]').scrollIntoView({block:'nearest'});});
      label.append(button,element('small',row.construct)); line.append(label,element('td',number(row.layer1_score,4)));
      cells.forEach(c=>line.append(element('td',number(row.activity[c].mean_log2_rna_dna))));
      const eligibility = element('td',reason(row)); if(!row.eligible) eligibility.className='coverage-missing';
      line.append(eligibility); fragment.append(line);
    }
    q('[data-experiment-rows]').replaceChildren(fragment);
    q('[data-experiment-row-count]').textContent=tr(`${rows.length} of 200 sequences shown.`,`${rows.length} de 200 secuencias visibles.`);
    q('[data-experiment-empty]').hidden=rows.length!==0;
  }
  function select(id) {
    selected = records.find(r=>r.probe_id===id); probeSelect.value=id;
    drawDetails(); drawPlot();
    // Preserve table button focus rather than rebuilding its focused row.
    q('[data-experiment-rows]').querySelectorAll('tr').forEach(row=>row.classList.toggle('is-selected',row.querySelector('button').textContent===id));
  }
  fetch(url).then(r=>{if(!r.ok)throw new Error('unavailable');return r.json();}).then(data=>{
    if(data.schema_version!==1 || data.status!=='exploratory_previously_exposed_200' || data.records?.length!==200) throw new Error('data');
    records=data.records;
    if(new Set(records.map(r=>r.probe_id)).size!==200 || records.some(r=>!/^probe_\d{4}$/.test(r.probe_id) ||
      !Number.isFinite(r.layer1_score) || cells.some(c=>!r.activity[c] ||
        (r.activity[c].mean_log2_rna_dna!==null && !Number.isFinite(r.activity[c].mean_log2_rna_dna))))) throw new Error('schema');
    eligible=records.filter(r=>r.eligible);
    if(eligible.length!==185 || eligible.some(r=>cells.some(c=>!Number.isFinite(r.activity[c].mean_log2_rna_dna) || !r.activity[c].coverage_pass))) throw new Error('coverage');
    const scores=eligible.map(r=>r.layer1_score), activities=eligible.flatMap(r=>cells.map(c=>r.activity[c].mean_log2_rna_dna));
    xDomain=[Math.floor(Math.min(...scores)),Math.ceil(Math.max(...scores))];
    yDomain=[Math.floor(Math.min(...activities)),Math.ceil(Math.max(...activities))];
    for(const row of records){const option=element('option',row.probe_id+' · '+row.construct);option.value=row.probe_id;probeSelect.append(option);}
    selected=records[0]; q('[data-experiment-panel]').hidden=false;
    drawDetails(); drawTable(); drawPlot();
    cellSelect.addEventListener('change',()=>{drawDetails();drawPlot();});
    probeSelect.addEventListener('change',()=>select(probeSelect.value));
    search.addEventListener('input',drawTable);coverage.addEventListener('change',drawTable);
    if('ResizeObserver' in window) new ResizeObserver(drawPlot).observe(plot);
  }).catch(()=>{q('[data-experiment-panel]').hidden=true;status.textContent=tr(
    'The interactive comparison could not load. The summary and CSV/JSON downloads remain available. Reload to try again.',
    'No se pudo cargar la comparación interactiva. El resumen y las descargas CSV/JSON siguen disponibles. Recarga para intentarlo de nuevo.');});
})();
