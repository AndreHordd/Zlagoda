// перемикач теми
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('theme-toggle');
  const body = document.body;
  // якщо в локалСторедж було 'dark' — ввімкнути
  if (localStorage.getItem('theme') === 'dark') {
    body.classList.add('dark-mode');
  }
  btn.addEventListener('click', () => {
    const dark = body.classList.toggle('dark-mode');
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  });
});
