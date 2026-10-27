/* User sequences stay in this page and its dedicated worker. */
(() => {
  'use strict';
  const app = document.querySelector('[data-predictor]');
  if (!app) return;
  const es = document.documentElement.lang === 'es';
  const tr = (en, spanish) => es ? spanish : en;
  const script = new URL(document.currentScript.src);
  const dataUrl = name => new URL('../data/' + name, script);
  const input = app.querySelector('#prediction-input');
  const file = app.querySelector('#prediction-file');
  const controls = app.querySelector('fieldset');
  const cancel = app.querySelector('[data-cancel]');
  const status = app.querySelector('[data-status]');
  const errorBox = app.querySelector('[data-error]');
  const progress = app.querySelector('progress');
  const results = app.querySelector('[data-results]');
  const body = app.querySelector('tbody');
  const comparison = app.querySelector('[data-comparison]');
  const differenceFilter = app.querySelector('[data-differences]');
  let worker = null, aborter = null, epoch = 0, lastRows = [], version = '', references = null, downloadUrl;
  const className = value => ({strong: tr('Strong enhancer', 'Potenciador fuerte'),
    weak: tr('Weak enhancer', 'Potenciador débil'), 'non-enhancer': tr('Non-enhancer', 'No potenciador')})[value];
  const messages = {
    empty: () => tr('Paste FASTA sequences or choose an input file.', 'Pega secuencias FASTA o elige un archivo.'),
    format: () => tr('Start each record with a >identifier line, followed by its DNA sequence.', 'Inicia cada registro con una línea >identificador, seguida de su secuencia de ADN.'),
    header: d => tr(`Record ${d.row} needs an identifier after >.`, `El registro ${d.row} necesita un identificador después de >.`),
    longHeader: d => tr(`Record ${d.row}: use an identifier of at most 500 characters.`, `Registro ${d.row}: usa un identificador de hasta 500 caracteres.`),
    alphabet: d => tr(`Record ${d.row} contains characters other than A, C, G, or T. Ambiguous bases such as N are not accepted.`, `El registro ${d.row} contiene caracteres distintos de A, C, G o T. No se aceptan bases ambiguas como N.`),
    length: d => tr(`Record ${d.row} has ${d.length} bases; exactly 200 are required. Sequences are never trimmed or padded automatically.`, `El registro ${d.row} tiene ${d.length} bases; se requieren exactamente 200. Las secuencias no se recortan ni se rellenan automáticamente.`),
    tooMany: () => tr('Use at most 1,000 sequences per run.', 'Usa hasta 1,000 secuencias por ejecución.'),
    tooLarge: () => tr('Use a text file or pasted input of at most 1 MiB.', 'Usa un archivo de texto o entrada de hasta 1 MiB.'),
    modelLoad: () => tr('The prediction model could not load. Check your connection and try again. No results were produced.', 'No se pudo cargar el modelo. Comprueba la conexión e inténtalo de nuevo. No se generaron resultados.'),
    modelIntegrity: () => tr('The model integrity check failed. Reload the page before trying again.', 'Falló la comprobación de integridad del modelo. Recarga la página antes de volver a intentarlo.'),
    fileRead: () => tr('The file could not be read. Choose a plain-text FASTA file.', 'No se pudo leer el archivo. Elige un archivo FASTA de texto.'),
    exampleLoad: () => tr('The example could not load. Check your connection and try again.', 'No se pudo cargar el ejemplo. Comprueba la conexión e inténtalo de nuevo.')
  };
  function busy(active) {
    controls.disabled = active;
    cancel.hidden = !active;
    app.setAttribute('aria-busy', String(active));
    if (!active) progress.hidden = true;
  }
  function discardResults() {
    results.hidden = true; comparison.hidden = true; lastRows = []; references = null;
    differenceFilter.checked = false;
    if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
  }
  function fail(code, detail = {}) {
    busy(false); discardResults();
    status.textContent = '';
    errorBox.textContent = (messages[code] || messages.modelLoad)(detail);
    errorBox.hidden = false;
  }
  function clearError() { errorBox.hidden = true; errorBox.textContent = ''; }
  function stop() {
    epoch++; aborter?.abort(); aborter = null; worker?.terminate(); worker = null;
    busy(false); discardResults(); clearError();
    status.textContent = tr('Cancelled. You can edit the input and start again.', 'Cancelado. Puedes editar la entrada y volver a empezar.');
  }
  cancel.addEventListener('click', stop);
  input.addEventListener('input', () => { discardResults(); clearError(); status.textContent = ''; });
  app.querySelector('[data-clear]').addEventListener('click', () => {
    stop(); input.value = ''; file.value = ''; status.textContent = ''; input.focus();
  });
  async function replaceInput(read, loading) {
    const current = ++epoch;
    clearError(); discardResults(); busy(true); status.textContent = loading;
    try {
      const text = await read();
      if (current !== epoch) return;
      input.value = text; file.value = '';
      EnhancerPredictor.parseFasta(text);
      busy(false);
      status.textContent = tr('Input loaded. Select Run predictions to begin.', 'Entrada cargada. Selecciona Ejecutar predicciones para comenzar.');
      input.focus();
    } catch (error) {
      if (current === epoch) fail(error.code || 'fileRead', error.detail);
    }
  }
  file.addEventListener('change', () => {
    const chosen = file.files[0];
    if (!chosen) return;
    if (chosen.size > EnhancerPredictor.MAX_BYTES) { fail('tooLarge'); return; }
    replaceInput(() => chosen.text(), tr('Reading file…', 'Leyendo archivo…'));
  });
  for (const button of app.querySelectorAll('[data-example]')) button.addEventListener('click', () => {
    aborter = new AbortController();
    replaceInput(async () => {
      const response = await fetch(dataUrl('ienhancer_2l_server_200_queries.fasta'), { signal: aborter.signal });
      if (!response.ok) throw new EnhancerPredictor.InputError('exampleLoad');
      const text = await response.text();
      if (button.dataset.example === '200') return text;
      const records = EnhancerPredictor.parseFasta(text);
      // One example from each saved local class; these are demonstrations, not test accuracy.
      return [records[0], records[1], records.find(row => row.header === 'probe_0089')]
        .map(row => '>' + row.header + '\n' + row.sequence).join('\n');
    }, tr('Loading example…', 'Cargando ejemplo…'));
  });
  function renderRows() {
    body.replaceChildren();
    const rows = lastRows.filter((row, i) => !differenceFilter.checked || row.predicted_class !== references[i].server_class);
    const fragment = document.createDocumentFragment();
    for (const row of rows) {
      const index = row.row_1_based - 1;
      const trElement = document.createElement('tr');
      const cell = (value, tag = 'td') => {
        const element = document.createElement(tag); element.textContent = value;
        if (tag === 'th') element.scope = 'row';
        trElement.append(element); return element;
      };
      cell(row.row_1_based); cell(row.header, 'th');
      const label = cell('');
      const badge = document.createElement('span'); badge.className = 'prediction-label prediction-' + row.predicted_class;
      badge.textContent = className(row.predicted_class); label.append(badge);
      cell(row.enhancer_decision_score.toFixed(8));
      cell(row.strength_decision_score === null ? '—' : row.strength_decision_score.toFixed(8));
      if (references) {
        cell(className(references[index].server_class));
        cell(row.predicted_class === references[index].server_class ? tr('Match', 'Coincide') : tr('Different', 'Diferente'));
      }
      fragment.append(trElement);
    }
    body.append(fragment);
    app.querySelector('[data-row-count]').textContent = tr(`Showing ${rows.length} of ${lastRows.length} predictions.`, `Se muestran ${rows.length} de ${lastRows.length} predicciones.`);
    app.querySelectorAll('[data-reference-heading]').forEach(el => { el.hidden = !references; });
  }
  differenceFilter.addEventListener('change', renderRows);
  async function finish(message, current) {
    let reference = null, referenceUnavailable = false;
    if (message.rows.length === 200) {
      try {
        const response = await fetch(dataUrl('predictor_reference_200.json'));
        if (!response.ok) throw new Error('reference');
        const saved = await response.json();
        if (saved.length === message.rows.length && saved.every((r, i) => r.sequence_sha256 === message.rows[i].sequence_sha256)) reference = saved;
      } catch { referenceUnavailable = true; }
    }
    if (current !== epoch) return;
    busy(false); lastRows = message.rows; version = message.version; references = reference;
    const counts = { strong: 0, weak: 0, 'non-enhancer': 0 };
    lastRows.forEach(row => counts[row.predicted_class]++);
    for (const key of Object.keys(counts)) app.querySelector(`[data-count="${key}"]`).textContent = counts[key];
    app.querySelector('[data-total]').textContent = lastRows.length;
    if (references) {
      const pythonMatches = lastRows.filter((row, i) => row.predicted_class === references[i].local_class).length;
      const authorMatches = lastRows.filter((row, i) => row.predicted_class === references[i].server_class).length;
      app.querySelector('[data-python-agreement]').textContent = `${pythonMatches} / ${lastRows.length}`;
      app.querySelector('[data-author-agreement]').textContent = `${authorMatches} / ${lastRows.length} (${(100 * authorMatches / lastRows.length).toFixed(1)}%)`;
      comparison.hidden = false;
    }
    renderRows();
    app.querySelector('[data-model-version]').textContent = version;
    downloadUrl = URL.createObjectURL(new Blob([EnhancerPredictor.toCsv(lastRows, version)], {type:'text/csv;charset=utf-8'}));
    app.querySelector('[data-download]').href = downloadUrl;
    results.hidden = false;
    status.textContent = tr(`Completed ${lastRows.length} predictions.`, `Se completaron ${lastRows.length} predicciones.`) +
      (referenceUnavailable ? tr(' Saved comparison data could not load; your predictions are available.', ' No se pudo cargar la comparación guardada; tus predicciones están disponibles.') : '');
    app.querySelector('#prediction-results-title').focus();
  }
  app.querySelector('form').addEventListener('submit', event => {
    event.preventDefault(); clearError(); discardResults();
    try { EnhancerPredictor.parseFasta(input.value); }
    catch (error) { fail(error.code, error.detail); input.focus(); return; }
    const current = ++epoch;
    busy(true); status.textContent = tr('Loading the saved models…', 'Cargando los modelos guardados…');
    try {
      if (!worker) worker = new Worker(new URL('predictor-worker.js', script));
      worker.onmessage = event => {
        if (current !== epoch) return;
        const message = event.data;
        if (message.type === 'progress') {
          progress.hidden = false; progress.max = message.total; progress.value = message.completed;
          status.textContent = tr(`Predicting ${message.completed} of ${message.total} sequences…`, `Prediciendo ${message.completed} de ${message.total} secuencias…`);
        } else if (message.type === 'error') {
          worker.terminate(); worker = null; fail(message.code, message.detail);
        } else if (message.type === 'done') finish(message, current).catch(() => { if (current === epoch) fail('modelLoad'); });
      };
      worker.onerror = () => { if (current === epoch) { worker?.terminate(); worker = null; fail('modelLoad'); } };
      worker.postMessage({ text: input.value });
    } catch { worker?.terminate(); worker = null; fail('modelLoad'); }
  });
  if (!('Worker' in window) || !('DecompressionStream' in window) || !window.crypto?.subtle) {
    status.textContent = tr('This tool needs a current browser with Web Workers, gzip decompression, and HTTPS. Try a recent Chrome, Edge, Firefox, or Safari.', 'Esta herramienta necesita un navegador actual con Web Workers, descompresión gzip y HTTPS. Prueba Chrome, Edge, Firefox o Safari recientes.');
  } else { controls.disabled = false; status.textContent = tr('Ready. Add sequences or load an example.', 'Listo. Añade secuencias o carga un ejemplo.'); }
  window.addEventListener('pagehide', event => {
    // A page in the back/forward cache keeps its worker and result download.
    if (!event.persisted) { worker?.terminate(); if (downloadUrl) URL.revokeObjectURL(downloadUrl); }
  });
})();
