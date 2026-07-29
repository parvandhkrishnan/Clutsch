import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/**
 * User-facing display preferences: theme and reduced-transparency.
 *
 * Deliberately separate from AuthContext, for two reasons:
 *  - these apply on public routes (/, /login, /sso-popup) where there is no user
 *  - AuthContext re-renders its whole subtree when `token` changes; coupling
 *    theme to it would make a login re-render for theme reasons and vice versa
 *
 * The theme is NOT initialised from localStorage here. A blocking script in
 * index.html has already read storage and stamped `data-theme` on <html>
 * before first paint (React cannot do that — even a lazy useState initialiser
 * runs after the browser has painted, which is a visible flash). So the source
 * of truth at mount is the DOM, and this provider just reads it back.
 */

const STORAGE_KEY = 'clutsch.prefs';

const PreferencesContext = createContext(null);

const readStored = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    // Malformed or unavailable (private mode, storage disabled) — fall back to
    // defaults rather than breaking render.
    return {};
  }
};

const writeStored = (patch) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readStored(), ...patch }));
  } catch {
    // Non-fatal: the preference still applies for this session.
  }
};

export const PreferencesProvider = ({ children }) => {
  // Read back what the bootstrap script already decided, so there is no
  // second opinion and no post-mount correction frame.
  const [theme, setThemeState] = useState(
    () => document.documentElement.dataset.theme || 'light'
  );
  // 'system' | 'light' | 'dark' — distinct from `theme`, which is always resolved.
  // Default matches the bootstrap script in index.html; both flip to 'system'
  // in the commit that lands the dark token set.
  const [themePreference, setThemePreferenceState] = useState(
    () => readStored().theme || 'light'
  );
  const [reduceTransparency, setReduceTransparencyState] = useState(
    () => !!readStored().reduceTransparency
  );

  const applyTheme = useCallback((resolved) => {
    const root = document.documentElement;
    root.dataset.theme = resolved;
    // Drives native scrollbars, checkboxes and Admin's range sliders for free.
    root.style.colorScheme = resolved;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = resolved === 'dark' ? '#0A1020' : '#EDF2FA';
    setThemeState(resolved);
  }, []);

  const setThemePreference = useCallback((pref) => {
    setThemePreferenceState(pref);
    writeStored({ theme: pref });
    const resolved =
      pref === 'system'
        ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : pref;
    applyTheme(resolved);
  }, [applyTheme]);

  const toggleTheme = useCallback(() => {
    setThemePreference(theme === 'dark' ? 'light' : 'dark');
  }, [theme, setThemePreference]);

  const setReduceTransparency = useCallback((value) => {
    setReduceTransparencyState(value);
    writeStored({ reduceTransparency: value });
    const root = document.documentElement;
    if (value) root.dataset.transparency = 'reduce';
    else delete root.dataset.transparency;
  }, []);

  // Follow the OS only while the user is on 'system'.
  useEffect(() => {
    if (themePreference !== 'system') return;
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e) => applyTheme(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [themePreference, applyTheme]);

  const value = useMemo(
    () => ({
      theme,
      themePreference,
      setThemePreference,
      toggleTheme,
      reduceTransparency,
      setReduceTransparency,
    }),
    [theme, themePreference, setThemePreference, toggleTheme, reduceTransparency, setReduceTransparency]
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
};

export const usePreferences = () => {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error('usePreferences must be used within a PreferencesProvider');
  return ctx;
};
