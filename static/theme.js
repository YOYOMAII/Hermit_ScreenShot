{
  const shell = document.querySelector('.app-shell');
  const appThemeToggle = document.querySelector('#app-theme-toggle');
  const APP_THEME_KEY = 'hermit-app-appearance';

  function applyAppTheme(mode) {
    const isDark = mode === 'dark';
    shell.classList.toggle('ui-dark', isDark);
    document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';
    appThemeToggle.setAttribute('aria-pressed', String(isDark));
    appThemeToggle.setAttribute(
      'aria-label',
      isDark ? 'Switch app to light mode' : 'Switch app to dark mode',
    );
    appThemeToggle.querySelector('.theme-toggle-icon').textContent = isDark ? '☀' : '☾';
    appThemeToggle.querySelector('.theme-toggle-label').textContent = isDark ? 'Light app' : 'Dark app';
    try {
      localStorage.setItem(APP_THEME_KEY, mode);
    } catch {
      // Ignore storage errors in restricted environments.
    }
  }

  function initialAppTheme() {
    try {
      const saved = localStorage.getItem(APP_THEME_KEY);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch {
      // Fall through to system preference.
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  applyAppTheme(initialAppTheme());
  appThemeToggle.addEventListener('click', () => {
    applyAppTheme(shell.classList.contains('ui-dark') ? 'light' : 'dark');
  });
}
