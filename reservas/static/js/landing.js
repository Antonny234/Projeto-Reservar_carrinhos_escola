(() => {
  const schoolInput = document.getElementById('busca-escola');
  const schoolItems = [...document.querySelectorAll('.school-link')];
  const schoolEmpty = document.getElementById('school-empty');

  if (!schoolInput || !schoolEmpty) return;

  const normalizeText = value => value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

  schoolInput.addEventListener('input', () => {
    const term = normalizeText(schoolInput.value.trim());
    let visible = 0;

    schoolItems.forEach(item => {
      const matches = normalizeText(item.dataset.search || '').includes(term);
      item.hidden = !matches;
      if (matches) visible += 1;
    });

    schoolEmpty.hidden = visible > 0 || schoolItems.length === 0;
  });
})();
