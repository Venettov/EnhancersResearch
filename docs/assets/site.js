(() => {
  // Real translated documents also work without JavaScript. Preserve a reader's
  // current section when following the switch, including in a new browser tab.
  const languageLinks = [...document.querySelectorAll('[data-language]')];
  const syncLanguageAnchors = () => {
    for (const link of languageLinks) {
      const url = new URL(link.href);
      url.hash = location.hash;
      link.href = url.href;
    }
  };
  syncLanguageAnchors();
  window.addEventListener('hashchange', syncLanguageAnchors);
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.primary-nav');
  if (menu && nav) {
    menu.hidden = false;
    document.documentElement.classList.add('has-js');
    const close = () => { menu.setAttribute('aria-expanded', 'false'); nav.classList.remove('is-open'); };
    menu.addEventListener('click', () => {
      const open = menu.getAttribute('aria-expanded') !== 'true';
      menu.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    });
    nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') { close(); menu.focus(); }
    });
    window.matchMedia('(min-width: 761px)').addEventListener('change', close);
  }

  const controls = document.querySelector('[data-publication-tools]');
  if (!controls) return;
  const search = document.getElementById('publication-search');
  const items = [...document.querySelectorAll('[data-publication]')];
  const filters = [...document.querySelectorAll('[data-filter]')];
  let selected = 'all';
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const update = () => {
    const query = normalize(search.value.trim());
    let count = 0;
    for (const item of items) {
      const visible = (selected === 'all' || item.dataset.type === selected) && normalize(item.textContent).includes(query);
      item.hidden = !visible;
      if (visible) count++;
    }
    for (const filter of filters) filter.setAttribute('aria-pressed', String(filter.dataset.filter === selected));
    document.getElementById('publication-count').textContent = document.documentElement.lang === 'es'
      ? `${count} de ${items.length} trabajos recopilados`
      : `${count} of ${items.length} collected works`;
    document.getElementById('publication-empty').hidden = count !== 0;
  };
  controls.hidden = false;
  search.addEventListener('input', update);
  filters.forEach(filter => filter.addEventListener('click', () => { selected = filter.dataset.filter; update(); }));
  document.querySelector('[data-clear-search]').addEventListener('click', () => { selected = 'all'; search.value = ''; update(); search.focus(); });
  const revealPublication = (id, scroll) => {
    const target = document.getElementById(id);
    if (target?.matches('[data-publication]') && target.hidden) {
      selected = 'all'; search.value = ''; update();
      if (scroll) target.scrollIntoView();
    }
  };
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (link) revealPublication(link.getAttribute('href').slice(1), false);
  });
  window.addEventListener('hashchange', () => revealPublication(location.hash.slice(1), true));
})();
