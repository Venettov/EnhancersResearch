(() => {
  const payload = document.getElementById('glossary-data');
  if (!payload) return;
  const { terms, ui } = JSON.parse(payload.textContent);
  const byId = new Map(terms.map(term => [term.id, term]));
  const dialog = document.getElementById('term-dialog');
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  // Ordinary anchors remain usable without JavaScript or dialog support.
  if (dialog && typeof dialog.showModal === 'function') {
    let opener;
    let previousOverflow;
    const fillLinks = (id, links) => {
      const section = document.getElementById(id);
      const list = section.querySelector('ul');
      list.replaceChildren();
      section.hidden = links.length === 0;
      for (const item of links) {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = item.url;
        a.textContent = item.label;
        li.append(a);
        list.append(li);
      }
    };
    document.querySelectorAll('[data-term]').forEach(link => {
      link.setAttribute('aria-haspopup', 'dialog');
      link.setAttribute('aria-controls', 'term-dialog');
    });
    document.addEventListener('click', event => {
      const link = event.target.closest('[data-term]');
      if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const term = byId.get(link.dataset.term);
      if (!term) return;
      event.preventDefault();
      opener = link;
      document.getElementById('term-category').textContent = ui.categories[term.category];
      document.getElementById('term-title').textContent = term.name;
      document.getElementById('term-definition').textContent = term.definition;
      document.getElementById('term-context').textContent = term.context;
      document.getElementById('term-entry-link').href = `glossary.html#term-${term.id}`;
      fillLinks('term-sources', term.sources);
      fillLinks('term-papers', term.papers);
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      dialog.showModal();
      dialog.scrollTop = 0;
      document.getElementById('term-title').focus({ preventScroll: true });
    });
    dialog.querySelector('[data-term-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const focusable = [...dialog.querySelectorAll('a[href], button:not([disabled])')].filter(el => el.getClientRects().length);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement.id === 'term-title')) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });
    // Only a complete pointer gesture on the backdrop dismisses the dialog.
    let backdropDown = false;
    const outside = event => {
      const bounds = dialog.getBoundingClientRect();
      return event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom);
    };
    dialog.addEventListener('pointerdown', event => { backdropDown = outside(event); });
    dialog.addEventListener('click', event => { if (backdropDown && outside(event)) dialog.close(); backdropDown = false; });
    dialog.addEventListener('close', () => {
      document.body.style.overflow = previousOverflow;
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    });
  }

  const tools = document.querySelector('[data-glossary-tools]');
  if (!tools) return;
  const search = document.getElementById('glossary-search');
  const topic = document.getElementById('glossary-topic');
  const cards = [...document.querySelectorAll('[data-glossary-entry]')];
  const haystacks = new Map(cards.map(card => [card, normalize(card.textContent + ' ' + card.dataset.aliases)]));
  const update = () => {
    const query = normalize(search.value.trim());
    let count = 0;
    for (const card of cards) {
      card.hidden = !(topic.value === 'all' || card.dataset.category === topic.value) || !haystacks.get(card).includes(query);
      if (!card.hidden) count++;
    }
    document.getElementById('glossary-count').textContent = `${count} / ${cards.length} ${ui.count}`;
    document.getElementById('glossary-empty').hidden = count !== 0;
  };
  const revealAnchor = () => {
    const card = document.getElementById(location.hash.slice(1));
    if (!card?.matches('[data-glossary-entry]')) return;
    if (card.hidden) { search.value = ''; topic.value = 'all'; update(); }
    card.scrollIntoView();
  };
  tools.hidden = false;
  search.addEventListener('input', update);
  topic.addEventListener('change', update);
  tools.querySelector('[data-glossary-clear]').addEventListener('click', () => {
    search.value = ''; topic.value = 'all'; update(); search.focus();
  });
  window.addEventListener('hashchange', revealAnchor);
  update();
  revealAnchor();
})();
