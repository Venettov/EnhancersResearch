/* A self-contained, script-free report. All user identifiers enter as text. */
(() => {
  'use strict';
  window.EnhancerReport = { create({ rows, version, references, completedAt, language }) {
    const es = language === 'es', tr = (en, spanish) => es ? spanish : en;
    const labels = {strong: tr('Strong enhancer', 'Potenciador fuerte'), weak: tr('Weak enhancer', 'Potenciador débil'),
      'non-enhancer': tr('Non-enhancer', 'No potenciador')};
    const doc = document.implementation.createHTMLDocument(tr('EnhancersResearch · Prediction report', 'EnhancersResearch · Informe de predicciones'));
    doc.documentElement.lang = es ? 'es' : 'en';
    const meta = doc.createElement('meta'); meta.setAttribute('charset','utf-8'); doc.head.prepend(meta);
    const viewport = doc.createElement('meta'); viewport.name = 'viewport'; viewport.content = 'width=device-width, initial-scale=1'; doc.head.append(viewport);
    const policy = doc.createElement('meta'); policy.httpEquiv = 'Content-Security-Policy';
    policy.content = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"; doc.head.append(policy);
    const style = doc.createElement('style');
    style.textContent = 'body{font:15px/1.6 system-ui,sans-serif;color:#193943;max-width:1100px;margin:40px auto;padding:0 24px}h1,h2{line-height:1.25}h1{color:#007c79}p{max-width:85ch}.note{background:#edf5f1;padding:16px;border-left:4px solid #007c79}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px;border-bottom:1px solid #cddad6;text-align:left;vertical-align:top;overflow-wrap:anywhere}thead{background:#edf5f1}tbody th{font-weight:500;max-width:260px}.hash{font:10px monospace;display:block;overflow-wrap:anywhere;margin-top:6px}code{overflow-wrap:anywhere}section{overflow-x:auto}@media print{body{margin:0;padding:0;font-size:10pt}table{font-size:8pt}thead{display:table-header-group}tr{break-inside:avoid}.print-help{display:none}@page{size:landscape;margin:14mm}}';
    doc.head.append(style);
    const add = (tag, text, parent = doc.body) => { const el = doc.createElement(tag); el.textContent = text; parent.append(el); return el; };
    add('h1', tr('Prediction report', 'Informe de predicciones'));
    add('p', 'EnhancersResearch · Jose Andres Riveraruiz · ' + tr('Advisor: Dr. Iman Dehzangi', 'Asesor: Dr. Iman Dehzangi'));
    add('p', tr('Completed: ', 'Finalizado: ') + completedAt.toLocaleString(es ? 'es' : 'en', {dateStyle:'long',timeStyle:'long'}));
    add('p', tr('Model version: ', 'Versión del modelo: ')); add('code', version);
    add('p', tr('Primary models trained on 13 October 2026. Each input contains exactly 200 A/C/G/T bases. Predictions were calculated in the browser; no sequences were uploaded.',
      'Modelos principales entrenados el 13 de octubre de 2026. Cada entrada contiene exactamente 200 bases A/C/G/T. Las predicciones se calcularon en el navegador; no se enviaron secuencias.'));
    add('p', tr('Open this file in a browser and choose Print to print or save as PDF. This report includes the entire batch in input order, regardless of table filters. Identifiers and sequence hashes are included; DNA sequences are not embedded.',
      'Abre este archivo en un navegador y selecciona Imprimir para imprimirlo o guardarlo como PDF. Incluye todo el lote en el orden de entrada, sin aplicar los filtros de la tabla. Contiene identificadores y hashes; no incluye las secuencias de ADN.')).className = 'print-help';
    add('h2', tr('Batch summary', 'Resumen del lote'));
    const counts = {strong:0,weak:0,'non-enhancer':0}; rows.forEach(row => counts[row.predicted_class]++);
    add('p', `${rows.length} ` + tr('sequences', 'secuencias') + ' · ' + Object.keys(counts).map(key => `${labels[key]}: ${counts[key]}`).join(' · '));
    if (references) {
      const matches = rows.filter((row,i) => row.predicted_class === references[i].server_class).length;
      add('p', tr('Agreement with the authors’ saved responses: ', 'Coincidencia con las respuestas guardadas de los autores: ') + `${matches}/${rows.length} (${(100*matches/rows.length).toFixed(1)}%). ` +
        tr('These exact inputs match the original comparison set. Author responses were saved on 19 October 2026; this run made no requests to their server. Agreement is not biological accuracy.',
          'Estas entradas exactas coinciden con el conjunto original de comparación. Las respuestas de los autores se guardaron el 19 de octubre de 2026; esta ejecución no consultó su servidor. La coincidencia no es exactitud biológica.'));
    }
    add('h2', tr('How to read the results', 'Cómo interpretar los resultados'));
    add('p', tr('Layer I: a score above zero predicts enhancer; zero or below predicts non-enhancer. Layer II is applied only to predicted enhancers: above zero predicts strong, otherwise weak. A dash means layer II was not applied. Scores are uncalibrated SVM decision values, not probabilities, confidence percentages, or measured activity. Scores near zero may be sensitive to numerical differences.',
      'Etapa I: una puntuación mayor que cero predice potenciador; cero o menos predice no potenciador. La etapa II se aplica solo a los potenciadores predichos: mayor que cero predice fuerte y, en otro caso, débil. Un guion indica que no se aplicó la etapa II. Son valores de decisión SVM no calibrados, no probabilidades, porcentajes de confianza ni actividad medida. Cerca de cero pueden ser sensibles a diferencias numéricas.')).className = 'note';
    add('p', tr('These historical benchmark labels do not establish experimental activity in any cell type. This report does not measure accuracy on your input. Sequence hashes identify the exact DNA; scores below retain full numerical precision.',
      'Estas etiquetas del conjunto histórico no establecen actividad experimental en ningún tipo celular. Este informe no mide la exactitud en tus entradas. Los hashes identifican el ADN exacto; las puntuaciones conservan la precisión numérica completa.'));
    add('h2', tr('All predictions', 'Todas las predicciones'));
    const section = add('section',''), table = add('table','',section);
    add('caption', tr('One row per input sequence; SHA-256 below each identifier.', 'Una fila por secuencia de entrada; SHA-256 debajo de cada identificador.'),table);
    const header = add('tr','',add('thead','',table));
    const headings = ['#',tr('Sequence ID / hash','ID de secuencia / hash'),tr('Our prediction','Nuestra predicción'),tr('Layer I score','Puntuación I'),tr('Layer II score','Puntuación II')];
    if (references) headings.push(tr('Authors’ saved prediction','Predicción guardada de los autores'),tr('Agreement','Coincidencia'));
    headings.forEach(value => { add('th',value,header).scope = 'col'; });
    const tbody = add('tbody','',table);
    rows.forEach((row,i) => {
      const line = add('tr','',tbody); add('td',String(row.row_1_based),line);
      const id = add('th',row.header,line); id.scope = 'row'; add('span',row.sequence_sha256,id).className = 'hash';
      add('td',labels[row.predicted_class],line); add('td',String(row.enhancer_decision_score),line);
      add('td',row.strength_decision_score === null ? '—' : String(row.strength_decision_score),line);
      if (references) { add('td',labels[references[i].server_class],line); add('td',row.predicted_class === references[i].server_class ? tr('Match','Coincide') : tr('Different','Diferente'),line); }
    });
    return '<!doctype html>\n' + doc.documentElement.outerHTML;
  }};
})();
