/* Frozen primary PseKNC/RBF-SVM inference. No fitting, thresholds, or source models change. */
(function (root) {
  'use strict';
  const MAX_RECORDS = 1000;
  const MAX_BYTES = 1024 * 1024;
  class InputError extends Error {
    constructor(code, detail = {}) { super(code); this.code = code; this.detail = detail; }
  }
  function parseFasta(text) {
    if (new TextEncoder().encode(text).length > MAX_BYTES) throw new InputError('tooLarge');
    const records = [];
    let current = null;
    for (const raw of text.replace(/^\uFEFF/, '').split(/\r\n?|\n/)) {
      const line = raw.trim();
      if (!line) continue;
      if (line.startsWith('>')) {
        const header = line.slice(1).trim();
        if (!header) throw new InputError('header', { row: records.length + 1 });
        if (header.length > 500) throw new InputError('longHeader', { row: records.length + 1 });
        current = { header, sequence: '' };
        records.push(current);
        if (records.length > MAX_RECORDS) throw new InputError('tooMany');
      } else {
        if (!current) throw new InputError('format');
        current.sequence += line.replace(/\s/g, '').toUpperCase();
      }
    }
    if (!records.length) throw new InputError('empty');
    records.forEach((record, i) => {
      const detail = { row: i + 1, length: record.sequence.length };
      if (/[^ACGT]/.test(record.sequence)) throw new InputError('alphabet', detail);
      if (record.sequence.length !== 200) throw new InputError('length', detail);
    });
    return records;
  }
  function components(sequence, table) {
    if (sequence.length !== 200 || /[^ACGT]/.test(sequence)) throw new InputError('length');
    const bases = Array.from(sequence, c => ({ A: 0, C: 1, G: 2, T: 3 })[c]);
    const counts = new Float64Array(4096);
    let word = 0;
    for (let i = 0; i < bases.length; i++) {
      word = ((word << 2) | bases[i]) & 4095;
      if (i >= 5) counts[word]++;
    }
    const frequencies = counts.map(n => n / 195);
    const pairs = bases.slice(0, -1).map((n, i) => n * 4 + bases[i + 1]);
    const theta = new Float64Array(9);
    for (let lag = 1; lag <= 9; lag++) {
      let sum = 0;
      for (let i = 0; i < 199 - lag; i++) {
        for (let property = 0; property < 6; property++) {
          const delta = table[pairs[i]][property] - table[pairs[i + lag]][property];
          sum += delta * delta;
        }
      }
      theta[lag - 1] = sum / ((199 - lag) * 6);
    }
    return { frequencies, theta };
  }
  function score(pieces, model) {
    const { frequencies, theta } = pieces;
    let total = 0;
    for (const value of frequencies) total += value;
    for (const value of theta) total += model.weight * value;
    const dots = new Float64Array(model.count);
    let norm = 0;
    for (let column = 0; column < 4096; column++) {
      const value = frequencies[column] / total;
      if (!value) continue;
      norm += value * value;
      for (let j = model.columnOffsets[column]; j < model.columnOffsets[column + 1]; j++) {
        dots[model.rowIndices[j]] += value * model.values[j];
      }
    }
    for (let column = 0; column < 9; column++) {
      const value = model.weight * theta[column] / total;
      norm += value * value;
      for (let row = 0; row < model.count; row++) dots[row] += value * model.structure[row * 9 + column];
    }
    // Compensated addition limits cancellation among large signed SVM coefficients.
    let sum = 0, correction = 0;
    for (let row = 0; row < model.count; row++) {
      const distance = Math.max(0, norm + model.norms[row] - 2 * dots[row]);
      const value = model.dual[row] * Math.exp(-model.gamma * distance) - correction;
      const next = sum + value;
      correction = (next - sum) - value;
      sum = next;
    }
    const result = sum + model.intercept;
    if (!Number.isFinite(result)) throw new Error('Invalid model result');
    return result;
  }
  function predict(sequence, model) {
    const pieces = components(sequence, model.properties);
    const enhancer = score(pieces, model.layers[0]);
    const strength = enhancer > 0 ? score(pieces, model.layers[1]) : null;
    return { predicted_class: strength === null ? 'non-enhancer' : strength > 0 ? 'strong' : 'weak',
             enhancer_decision_score: enhancer, strength_decision_score: strength };
  }
  function csvCell(value) {
    let text = value === null || value === undefined ? '' : String(value);
    // Keep user-provided identifiers literal in spreadsheet applications.
    if (typeof value === 'string' && /^[\s]*[=+@-]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function toCsv(rows, version) {
    const fields = ['row_1_based', 'header', 'sequence_sha256', 'predicted_class',
                    'enhancer_decision_score', 'strength_decision_score', 'model_version'];
    return fields.join(',') + '\r\n' + rows.map(row => fields.map(field =>
      csvCell(field === 'model_version' ? version : row[field])).join(',')).join('\r\n') + '\r\n';
  }
  const api = { parseFasta, components, score, predict, toCsv, InputError, MAX_RECORDS, MAX_BYTES };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.EnhancerPredictor = api;
})(globalThis);
