'use strict';
importScripts('predictor-engine.js');
let cachedModel;
let cachedManifest;
const hex = buffer => Array.from(new Uint8Array(buffer), n => n.toString(16).padStart(2, '0')).join('');
async function loadModel() {
  if (cachedModel) return;
  const manifestResponse = await fetch('../data/predictor_manifest.json');
  if (!manifestResponse.ok) throw new Error('modelLoad');
  const manifest = await manifestResponse.json();
  if (!/^ienhancer-primary-[a-z0-9-]+\.json\.gz$/.test(manifest.file)) throw new Error('modelLoad');
  const response = await fetch(new URL('../data/' + manifest.file, self.location.href));
  if (!response.ok) throw new Error('modelLoad');
  const bytes = await response.arrayBuffer();
  if (hex(await crypto.subtle.digest('SHA-256', bytes)) !== manifest.sha256) throw new Error('modelIntegrity');
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  const model = await new Response(stream).json();
  if (model.version !== manifest.version || model.properties.length !== 16 || model.layers.length !== 2)
    throw new Error('modelIntegrity');
  cachedModel = model;
  cachedManifest = manifest;
}
self.onmessage = async event => {
  try {
    const records = EnhancerPredictor.parseFasta(event.data.text);
    self.postMessage({ type: 'loading', total: records.length });
    await loadModel();
    const rows = [];
    for (let i = 0; i < records.length; i++) {
      const { header, sequence } = records[i];
      const prediction = EnhancerPredictor.predict(sequence, cachedModel);
      rows.push({ row_1_based: i + 1, header,
                  sequence_sha256: hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(sequence))),
                  ...prediction });
      if ((i + 1) % 5 === 0 || i + 1 === records.length)
        self.postMessage({ type: 'progress', completed: i + 1, total: records.length });
    }
    self.postMessage({ type: 'done', rows, version: cachedManifest.version });
  } catch (error) {
    self.postMessage({ type: 'error', code: error.code || (['modelIntegrity', 'modelLoad'].includes(error.message) ? error.message : 'modelLoad'), detail: error.detail });
  }
};
