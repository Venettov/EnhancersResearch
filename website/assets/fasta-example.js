/* The ordinary file links remain usable without JavaScript or dialog support. */
(() => {
  'use strict';
  const dialog = document.getElementById('fasta-example-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const title = dialog.querySelector('h2');
  const status = dialog.querySelector('[data-fasta-status]');
  const copy = dialog.querySelector('[data-fasta-copy]');
  const es = document.documentElement.lang === 'es';
  let opener, previousOverflow, backdropDown = false;
  document.querySelectorAll('[data-fasta-example]').forEach(link => {
    link.setAttribute('aria-haspopup', 'dialog');
    link.setAttribute('aria-controls', dialog.id);
    link.addEventListener('click', event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      status.textContent = '';
      dialog.showModal();
      dialog.scrollTop = 0;
      title.focus({preventScroll: true});
    });
  });
  dialog.querySelector('[data-fasta-close]').addEventListener('click', () => dialog.close());
  const outside = event => {
    const bounds = dialog.getBoundingClientRect();
    return event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom);
  };
  dialog.addEventListener('pointerdown', event => { backdropDown = outside(event); });
  dialog.addEventListener('click', event => {
    if (backdropDown && outside(event)) dialog.close();
    backdropDown = false;
  });
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('a[href], button:not([disabled])')];
    if (event.shiftKey && (document.activeElement === controls[0] || document.activeElement === title)) {
      event.preventDefault(); controls.at(-1).focus();
    } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
      event.preventDefault(); controls[0].focus();
    }
  });
  dialog.addEventListener('close', () => {
    document.body.style.overflow = previousOverflow;
    opener?.focus({preventScroll: true});
  });
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(dialog.querySelector('[data-fasta-content]').textContent);
      status.textContent = es ? 'Ejemplo copiado. Pégalo en el campo de secuencias.' : 'Example copied. Paste it into the sequence input.';
    } catch {
      status.textContent = es ? 'No se pudo copiar automáticamente. Selecciona y copia el bloque o descarga el archivo.' : 'Automatic copying was unavailable. Select and copy the block, or download the file.';
    }
  });
})();
