import { readonly, ref } from 'vue';

export type ThemePreference = 'system' | 'light' | 'dark';

const storageKey = 'klinkrr-theme';
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');

function readPreference(): ThemePreference {
  try {
    const saved = localStorage.getItem(storageKey);

    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
  } catch {
    // Browser storage may be unavailable.
  }

  return 'system';
}

const preference = ref<ThemePreference>(readPreference());

function applyTheme() {
  const theme =
    preference.value === 'system'
      ? systemTheme.matches
        ? 'dark'
        : 'light'
      : preference.value;

  document.documentElement.dataset.theme = theme;
}

function setTheme(value: ThemePreference) {
  preference.value = value;
  applyTheme();

  try {
    if (value === 'system') {
      localStorage.removeItem(storageKey);
    } else {
      localStorage.setItem(storageKey, value);
    }
  } catch {
    // The selection still works for this visit.
  }
}

systemTheme.addEventListener('change', applyTheme);
applyTheme();

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    systemTheme.removeEventListener('change', applyTheme);
  });
}

export function useTheme() {
  return {
    preference: readonly(preference),
    setTheme,
  };
}
